"""CSV / TXT export (§10 of the TZ).

Column order is fixed by §10. TXT is the tab-separated equivalent for the
"select-all + copy" flow used across the rest of the software.
"""

from __future__ import annotations

import csv
import io

from .pipeline import ResultRow

# §10 result columns, in order.
BASE_COLUMNS = [
    "Target", "tier", "score", "reject_reason", "Domain Rating", "rd_fol",
    "fol_share", "bl_rd", "subnet_div", "burn", "Organic / Traffic", "cc",
    "tld", "flag_spam_floor", "flag_burn", "flag_geo_review", "flag_cjk",
    "tier_override_reason",
]


def _format_cell(key: str, value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if key == "score" and isinstance(value, float):
        return f"{value:.1f}"
    if key in ("fol_share", "bl_rd", "subnet_div") and isinstance(value, (int, float)):
        return f"{value:.2f}"
    if key == "burn" and isinstance(value, (int, float)):
        return f"{value:.1f}"
    return str(value)


def _columns(rows: list[ResultRow], include_raw: bool) -> list[str]:
    cols = list(BASE_COLUMNS)
    if include_raw and rows:
        raw_keys: list[str] = []
        for row in rows:
            for k in row.raw.keys():
                key = f"src::{k}"
                if key not in raw_keys:
                    raw_keys.append(key)
        cols += raw_keys
    return cols


def to_csv(rows: list[ResultRow], include_raw: bool = False) -> str:
    cols = _columns(rows, include_raw)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(cols)
    for row in rows:
        d = row.to_dict(include_raw=include_raw)
        writer.writerow([_format_cell(c, d.get(c)) for c in cols])
    return buf.getvalue()


def to_txt(rows: list[ResultRow], include_raw: bool = False) -> str:
    """Tab-separated, for select-all + copy into a spreadsheet."""
    cols = _columns(rows, include_raw)
    lines = ["\t".join(cols)]
    for row in rows:
        d = row.to_dict(include_raw=include_raw)
        lines.append("\t".join(_format_cell(c, d.get(c)) for c in cols))
    return "\n".join(lines)
