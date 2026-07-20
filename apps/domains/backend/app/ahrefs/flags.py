"""Flags (§8 of the TZ). Computed for *all* domains.

Soft flags only mark; the red CJK flag can override the tier (handled in the
pipeline, which reads ``flag_cjk`` + ``cjk.action``).
"""

from __future__ import annotations

from dataclasses import dataclass

from .metrics import DomainRecord


@dataclass
class Flags:
    spam_floor: bool = False
    burn: bool = False
    geo_review: bool = False
    cjk: bool = False


def compute_flags(rec: DomainRecord, cfg: dict) -> Flags:
    f = cfg["flags"]

    # §8.1 flag_spam_floor
    sf = f["spam_floor"]
    spam_floor = (
        sf["rd_all_min"] <= rec.rd_all <= sf["rd_all_max"]
        and rec.fol_share < sf["fol_share_max"]
        and rec.org == sf["org_eq"]
    )

    # §8.1 flag_burn (softer threshold than reject)
    burn = rec.burn > f["burn"]["burn_min"]

    # §8.1 flag_geo_review: cc set AND not in a non-empty allowlist
    allowlist = [c.lower() for c in f["geo"].get("allowlist", [])]
    geo_review = bool(rec.cc) and len(allowlist) > 0 and rec.cc not in allowlist

    # §8.2 flag_cjk
    cjk_set = [c.lower() for c in f["cjk"].get("set", [])]
    cjk = bool(rec.cc) and rec.cc in cjk_set

    return Flags(spam_floor=spam_floor, burn=burn, geo_review=geo_review, cjk=cjk)
