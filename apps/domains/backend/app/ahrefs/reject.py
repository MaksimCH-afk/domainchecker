"""Hard-reject rules (§5 of the TZ).

A domain is REJECTed if *any* rule is true. Rules are checked in a fixed order
and the first triggered code is reported as ``reject_reason``.
"""

from __future__ import annotations

from typing import Optional

from .metrics import DomainRecord

# Order matters only for which reason is reported first (§5).
REJECT_ORDER = ["dead", "dr_floor", "spam_blast", "thin", "burn_hacked", "spam_floor_reject"]


def check_reject(rec: DomainRecord, cfg: dict) -> Optional[str]:
    """Return the first triggered reject code, or None if the domain passes."""
    r = cfg["reject"]

    # dead: DR == 0 AND rd_fol == 0 (kept first as the most descriptive reason)
    d = r["dead"]
    if rec.dr == d["dr_eq"] and rec.rd_fol == d["rd_fol_eq"]:
        return "dead"

    # dr_floor (Correction 1а): DR < dr_min. Catches DR=0 domains that carry
    # followed ref.domains and thus escape dead/thin.
    if "dr_floor" in r and rec.dr < r["dr_floor"]["dr_min"]:
        return "dr_floor"

    # spam_blast: rd_fol == 0 AND bl_rd_min <= bl_rd <= bl_rd_max AND rd_all >= rd_all_min
    sb = r["spam_blast"]
    if (
        rec.rd_fol == sb["rd_fol_eq"]
        and sb["bl_rd_min"] <= rec.bl_rd <= sb["bl_rd_max"]
        and rec.rd_all >= sb["rd_all_min"]
    ):
        return "spam_blast"

    # thin: rd_fol < rd_fol_max AND DR < dr_max
    t = r["thin"]
    if rec.rd_fol < t["rd_fol_max"] and rec.dr < t["dr_max"]:
        return "thin"

    # burn_hacked: burn > burn_min AND DR < dr_max AND org == 0
    bh = r["burn_hacked"]
    if rec.burn > bh["burn_min"] and rec.dr < bh["dr_max"] and rec.org == bh["org_eq"]:
        return "burn_hacked"

    # spam_floor_reject (Correction 1б, optional): fol_share < max AND
    # bl_rd <= max AND org == 0. Off by default; enable in settings.
    sfr = r.get("spam_floor_reject")
    if sfr and sfr.get("enabled") and (
        rec.fol_share < sfr["fol_share_max"]
        and rec.bl_rd <= sfr["bl_rd_max"]
        and rec.org == sfr["org_eq"]
    ):
        return "spam_floor_reject"

    return None
