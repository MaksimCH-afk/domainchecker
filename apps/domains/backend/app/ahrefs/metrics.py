"""Derived metrics & the normalized record (§3, §4 of the TZ)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import parsing


def _safe_div(numer: float, denom: float) -> float:
    """Division guarded per §4: division by 0 -> 0."""
    if denom == 0:
        return 0.0
    return numer / denom


@dataclass
class DomainRecord:
    """One normalized domain row with derived metrics.

    Built once at load time; the scoring pipeline is a pure function of these
    fields plus the config, so recompute never re-parses.
    """

    target: str
    dr: float
    rd_all: float
    rd_fol: float
    bl: float
    org: float
    ips: float
    subnets: float
    out_links: float
    cc: Optional[str]
    cc_traffic: Optional[int]
    tld: Optional[str]

    # derived (§4)
    fol_share: float = 0.0
    bl_rd: float = 0.0
    subnet_div: float = 0.0
    burn: float = 0.0

    # full passthrough of the original Ahrefs row (optional column dump in §10)
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: dict) -> "DomainRecord":
        n = parsing.to_number
        cc, cc_traffic = parsing.parse_top_countries(row.get("Organic / Top Countries"))
        rec = cls(
            target=parsing.normalize_target(row.get("Target")),
            dr=n(row.get("Domain Rating")),
            rd_all=n(row.get("Ref. domains / All")),
            rd_fol=n(row.get("Ref. domains / Followed")),
            bl=n(row.get("Backlinks / All")),
            org=n(row.get("Organic / Traffic")),
            ips=n(row.get("Ref. IPs / IPs")),
            subnets=n(row.get("Ref. IPs / Subnets")),
            out_links=n(row.get("Outgoing links / All time")),
            cc=cc,
            cc_traffic=cc_traffic,
            tld=parsing.parse_tld(row.get("Target")),
            raw=dict(row),
        )
        rec._compute_derived()
        return rec

    def _compute_derived(self) -> None:
        self.fol_share = _safe_div(self.rd_fol, self.rd_all)
        self.bl_rd = _safe_div(self.bl, self.rd_all)
        self.subnet_div = _safe_div(self.subnets, self.ips)
        self.burn = _safe_div(self.out_links, self.rd_all)
