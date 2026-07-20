"""Fixed bucket rules (§6 of TZ-2). No language settings — by design.

Applied in order, first match wins:
  1. confidence < threshold OR verdict == error -> Review
  2. verdict == bad                              -> Bad
  3. is_english_name == false                    -> Review
  4. otherwise                                   -> Good
"""

from __future__ import annotations

from .schema import Classification

GOOD = "good"
BAD = "bad"
REVIEW = "review"


def assign_bucket(c: Classification, confidence_threshold: float) -> str:
    if c.verdict == "error" or c.confidence < confidence_threshold:
        return REVIEW
    if c.verdict == "bad":
        return BAD
    if not c.is_english_name:
        return REVIEW
    return GOOD
