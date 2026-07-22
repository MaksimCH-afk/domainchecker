"""End-to-end analysis pipeline (§5-§8, §10, §11 of the TZ).

`analyze(records, config)` is a pure function: same rows + same config ->
same output. That is what makes the "recompute on config change without
re-upload" requirement (§9) cheap — the API keeps parsed `DomainRecord`s in
memory and only re-runs this.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .flags import Flags, compute_flags
from .metrics import DomainRecord
from .reject import check_reject
from .scoring import compute_score

TIERS = ["A", "B", "C", "Review", "Rejected"]
REJECT_REASONS = [
    "dead", "dr_floor", "spam_blast", "thin", "burn_hacked", "spam_floor_reject",
]


@dataclass
class ResultRow:
    target: str
    tier: str
    score: Optional[float]  # None for Rejected
    reject_reason: Optional[str]
    dr: float
    rd_fol: float
    fol_share: float
    bl_rd: float
    subnet_div: float
    burn: float
    org: float
    cc: Optional[str]
    tld: Optional[str]
    flags: Flags
    tier_override_reason: Optional[str]
    raw: dict = field(default_factory=dict)

    def to_dict(self, include_raw: bool = False) -> dict:
        d = {
            "Target": self.target,
            "tier": self.tier,
            "score": None if self.score is None else round(self.score, 1),
            "reject_reason": self.reject_reason or "",
            "Domain Rating": self.dr,
            "rd_fol": self.rd_fol,
            "fol_share": round(self.fol_share, 2),
            "bl_rd": round(self.bl_rd, 2),
            "subnet_div": round(self.subnet_div, 2),
            "burn": round(self.burn, 1),
            "Organic / Traffic": self.org,
            "cc": self.cc or "",
            "tld": self.tld or "",
            "flag_spam_floor": self.flags.spam_floor,
            "flag_burn": self.flags.burn,
            "flag_geo_review": self.flags.geo_review,
            "flag_cjk": self.flags.cjk,
            "tier_override_reason": self.tier_override_reason or "",
        }
        if include_raw:
            # Prefix passthrough keys so they never collide with result columns.
            for k, v in self.raw.items():
                d[f"src::{k}"] = v
        return d


def _tier_by_score(score: float, cfg: dict) -> str:
    t = cfg["tiers"]
    if score >= t["A_min"]:
        return "A"
    if score >= t["B_min"]:
        return "B"
    if score >= t["C_min"]:
        return "C"
    return "Review"


def evaluate(rec: DomainRecord, cfg: dict) -> ResultRow:
    """Score/tier/flag a single record (§7 assignment order)."""
    flags = compute_flags(rec, cfg)
    reject_reason = check_reject(rec, cfg)

    # (1) REJECT -> Rejected, no score.
    if reject_reason is not None:
        return ResultRow(
            target=rec.target, tier="Rejected", score=None,
            reject_reason=reject_reason, dr=rec.dr, rd_fol=rec.rd_fol,
            fol_share=rec.fol_share, bl_rd=rec.bl_rd, subnet_div=rec.subnet_div,
            burn=rec.burn, org=rec.org, cc=rec.cc, tld=rec.tld, flags=flags,
            tier_override_reason=None, raw=rec.raw,
        )

    score = compute_score(rec, cfg)
    override_reason: Optional[str] = None

    # (2) Red CJK flag overrides the tier, depending on cjk.action.
    cjk_action = cfg["flags"]["cjk"].get("action", "review")
    if flags.cjk and cjk_action == "reject":
        return ResultRow(
            target=rec.target, tier="Rejected", score=None,
            reject_reason=None, dr=rec.dr, rd_fol=rec.rd_fol,
            fol_share=rec.fol_share, bl_rd=rec.bl_rd, subnet_div=rec.subnet_div,
            burn=rec.burn, org=rec.org, cc=rec.cc, tld=rec.tld, flags=flags,
            tier_override_reason="cjk", raw=rec.raw,
        )
    if flags.cjk and cjk_action == "review":
        tier = "Review"
        override_reason = "cjk"
    else:
        # (3) tier by score thresholds (flag_only leaves scoring untouched).
        tier = _tier_by_score(score, cfg)

    return ResultRow(
        target=rec.target, tier=tier, score=score, reject_reason=None,
        dr=rec.dr, rd_fol=rec.rd_fol, fol_share=rec.fol_share, bl_rd=rec.bl_rd,
        subnet_div=rec.subnet_div, burn=rec.burn, org=rec.org, cc=rec.cc,
        tld=rec.tld, flags=flags, tier_override_reason=override_reason,
        raw=rec.raw,
    )


def summarize(rows: list[ResultRow], total_input: int, duplicates: int) -> dict:
    """§10 summary: counts/% per tier, per reject reason, per flag."""
    n = len(rows)
    tier_counts = {t: 0 for t in TIERS}
    reason_counts = {r: 0 for r in REJECT_REASONS}
    flag_counts = {
        "flag_spam_floor": 0, "flag_burn": 0,
        "flag_geo_review": 0, "flag_cjk": 0,
    }
    override_counts = {"cjk": 0}

    for row in rows:
        tier_counts[row.tier] += 1
        if row.reject_reason in reason_counts:
            reason_counts[row.reject_reason] += 1
        if row.flags.spam_floor:
            flag_counts["flag_spam_floor"] += 1
        if row.flags.burn:
            flag_counts["flag_burn"] += 1
        if row.flags.geo_review:
            flag_counts["flag_geo_review"] += 1
        if row.flags.cjk:
            flag_counts["flag_cjk"] += 1
        if row.tier_override_reason == "cjk":
            override_counts["cjk"] += 1

    def pct(c: int) -> float:
        return round(100.0 * c / n, 1) if n else 0.0

    return {
        "total_input_rows": total_input,
        "duplicates_removed": duplicates,
        "analyzed": n,
        "tiers": {t: {"count": c, "pct": pct(c)} for t, c in tier_counts.items()},
        "reject_reasons": {
            r: {"count": c, "pct": pct(c)} for r, c in reason_counts.items()
        },
        "flags": {f: {"count": c, "pct": pct(c)} for f, c in flag_counts.items()},
        "tier_overrides": override_counts,
    }


# Sort key (§10 default): Rejected last; the rest by score descending.
def _sort_key(row: ResultRow):
    is_rejected = 1 if row.tier == "Rejected" else 0
    score = row.score if row.score is not None else -1.0
    return (is_rejected, -score)


def analyze(records: list[DomainRecord], cfg: dict) -> tuple[list[ResultRow], dict]:
    """Run the full pipeline over pre-parsed, pre-deduped records."""
    rows = [evaluate(rec, cfg) for rec in records]
    rows.sort(key=_sort_key)
    summary = summarize(rows, total_input=len(records), duplicates=0)
    return rows, summary
