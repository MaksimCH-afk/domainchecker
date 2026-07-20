"""Domain input normalization & validation (FR-1..FR-4 of TZ-2).

No language / category logic here — that is the model's job. This layer only
cleans the raw pasted text into canonical domains, dedups, and flags non-domains
as errors (they never go to the model).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.IGNORECASE)
# A permissive domain shape: labels of a-z0-9/hyphen (punycode xn-- allowed),
# at least one dot, TLD of 2+ letters. Foreign *names* are still ASCII here.
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


def normalize_domain(raw: str) -> str:
    """FR-2: lowercase; drop scheme, www., path/query, trailing dot."""
    s = (raw or "").strip().lower()
    if not s:
        return ""
    s = _SCHEME_RE.sub("", s)
    s = s.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if s.startswith("www."):
        s = s[4:]
    s = s.rstrip(".")
    return s


def is_valid_domain(domain: str) -> bool:
    return bool(_DOMAIN_RE.match(domain))


@dataclass
class ParsedInput:
    # unique, valid, normalized domains to send to the model
    domains: list[str] = field(default_factory=list)
    # normalized -> first original spelling seen (FR-3)
    original: dict[str, str] = field(default_factory=dict)
    # normalized domains that failed validation (FR-4) -> raw spelling
    invalid: dict[str, str] = field(default_factory=dict)
    recognized: int = 0
    duplicates: int = 0


def parse_input(text: str) -> ParsedInput:
    """FR-1/3/4: split lines, normalize, dedup, split valid vs invalid."""
    result = ParsedInput()
    seen: set[str] = set()
    for line in (text or "").splitlines():
        raw = line.strip()
        if not raw:
            continue
        result.recognized += 1
        norm = normalize_domain(raw)
        if not norm:
            continue
        if norm in seen:
            result.duplicates += 1
            continue
        seen.add(norm)
        if is_valid_domain(norm):
            result.domains.append(norm)
            result.original[norm] = raw
        else:
            result.invalid[norm] = raw
    return result
