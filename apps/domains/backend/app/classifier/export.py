"""CSV / TXT export for classifier results (UI-7 of TZ-2).

CSV is the full table; TXT is just the domains of the current selection (for
the select-all + copy flow, default output format §2.6)."""

from __future__ import annotations

import csv
import io

COLUMNS = [
    "domain", "original", "bucket", "verdict", "category", "name_language",
    "is_english_name", "confidence", "matched_terms", "reason",
]


def to_csv(results: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for r in results:
        w.writerow([
            r["domain"], r["original"], r["bucket"], r["verdict"], r["category"],
            r["name_language"], "1" if r["is_english_name"] else "0",
            f"{r['confidence']:.2f}", " ".join(r.get("matched_terms", [])),
            r["reason"],
        ])
    return buf.getvalue()


def to_txt(results: list[dict]) -> str:
    """Domains only, one per line."""
    return "\n".join(r["domain"] for r in results)
