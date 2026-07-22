"""Validate & coerce the model's JSON response (FR-9, FR-10 of TZ-2)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from .instruction import CATEGORIES


@dataclass
class Classification:
    domain: str
    verdict: str            # good | bad | error
    category: str
    name_language: str      # reference only (Correction 1)
    is_english_name: bool   # reference only (Correction 1)
    matched_terms: list[str] = field(default_factory=list)
    confidence: float = 0.0  # reference only (Correction 1/4)
    reason: str = ""
    # Correction 1: optional red flag — model can't choose clean vs a bad
    # category and asks for manual review.
    needs_review: bool = False

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "verdict": self.verdict,
            "category": self.category,
            "name_language": self.name_language,
            "is_english_name": self.is_english_name,
            "matched_terms": self.matched_terms,
            "confidence": self.confidence,
            "reason": self.reason,
            "needs_review": self.needs_review,
        }


def error_result(domain: str, reason: str) -> Classification:
    return Classification(
        domain=domain, verdict="error", category="", name_language="",
        is_english_name=False, matched_terms=[], confidence=0.0, reason=reason,
        needs_review=False,
    )


def _extract_json_array(content: str):
    """Tolerate stray prose / code fences around the JSON array."""
    content = content.strip()
    content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # Fall back to the first [...] block.
    m = re.search(r"\[.*\]", content, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError("no JSON array in model response")


def _coerce_item(obj: dict) -> Optional[Classification]:
    if not isinstance(obj, dict) or "domain" not in obj:
        return None
    verdict = str(obj.get("verdict", "")).lower()
    if verdict not in ("good", "bad"):
        return None
    category = str(obj.get("category", "")).lower()
    if category not in CATEGORIES:
        category = "clean" if verdict == "good" else "pattern"
    try:
        confidence = float(obj.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    terms = obj.get("matched_terms") or []
    if not isinstance(terms, list):
        terms = []
    return Classification(
        domain=str(obj["domain"]).strip().lower(),
        verdict=verdict,
        category=category,
        name_language=str(obj.get("name_language", "")).lower(),
        is_english_name=bool(obj.get("is_english_name", False)),
        matched_terms=[str(t) for t in terms],
        confidence=confidence,
        reason=str(obj.get("reason", "")),
        needs_review=bool(obj.get("needs_review", False)),
    )


def parse_response(content: str, expected: list[str]) -> dict[str, Classification]:
    """Parse a batch response into {domain: Classification}.

    Raises ValueError if the payload is unusable (caller retries once, then
    marks the batch's domains as error per FR-10).
    """
    data = _extract_json_array(content)
    if not isinstance(data, list):
        raise ValueError("model response is not a JSON array")

    by_domain: dict[str, Classification] = {}
    for obj in data:
        item = _coerce_item(obj)
        if item is not None:
            by_domain[item.domain] = item

    # Map back to the exact domains we asked about (case-insensitive).
    result: dict[str, Classification] = {}
    for dom in expected:
        hit = by_domain.get(dom) or by_domain.get(dom.lower())
        if hit is None:
            raise ValueError(f"missing domain in response: {dom}")
        hit.domain = dom
        result[dom] = hit
    return result
