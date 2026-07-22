"""Fixed bucket rules — Correction 1 (raskladka by verdict only).

Neither the name language nor `confidence` affect the bucket anymore. They stay
in the response purely as reference columns. Applied in order, first match wins:
  1. verdict == error / invalid / unparsed        -> Review
  2. needs_review == true (model can't decide)     -> Review
  3. verdict == bad (any category, category rules) -> Bad
  4. verdict == good                               -> Good
"""

from __future__ import annotations

from .schema import Classification

GOOD = "good"
BAD = "bad"
REVIEW = "review"


def assign_bucket(c: Classification) -> str:
    if c.verdict == "error":
        return REVIEW
    if c.needs_review:
        return REVIEW
    if c.verdict == "bad":
        return BAD
    return GOOD  # verdict == good, any language
