"""Composite quality score (§6 of the TZ).

Logarithmic normalization damps the order-of-magnitude skew of the metrics.
"""

from __future__ import annotations

import math

from .metrics import DomainRecord


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def norm(x: float, cap: float) -> float:
    """norm(x, cap) = clip(ln(1 + max(x, 0)) / ln(1 + cap), 0, 1)."""
    if cap <= 0:
        return 0.0
    return _clip(math.log1p(max(x, 0.0)) / math.log1p(cap), 0.0, 1.0)


def compute_score(rec: DomainRecord, cfg: dict) -> float:
    """Return score in [0, 100] for a domain that passed REJECT."""
    s = cfg["score"]
    w = s["weights"]
    caps = s["caps"]
    sp = s["spam_pen"]

    qual = _clip(rec.fol_share, 0.0, 1.0)  # anti-nofollow-spam multiplier

    # spam_pen = 1 - clip(bl_rd - base, 0, cap) / cap
    pen_cap = sp["cap"]
    spam_pen = 1.0 - _clip(rec.bl_rd - sp["bl_rd_base"], 0.0, pen_cap) / pen_cap

    score = 100.0 * (
        w["dr"] * norm(rec.dr, caps["dr"])
        + w["rd_fol"] * norm(rec.rd_fol, caps["rd_fol"]) * qual
        + w["subnets"] * norm(rec.subnets, caps["subnets"])
        + w["org"] * norm(rec.org, caps["org"])
        + w["spam_pen"] * spam_pen
    )
    return score
