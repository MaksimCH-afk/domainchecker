"""Parsing & normalization of Ahrefs Batch Analysis rows (§3 of the TZ).

Field mapping is by *header name*, not by index. Everything here is defensive:
empty / non-numeric metric values become 0, malformed geo becomes null, and we
never raise on a single bad cell.
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# §2.1 Expected Ahrefs headers (35 columns). Extra/unknown columns are ignored.
# ---------------------------------------------------------------------------
AHREFS_COLUMNS = [
    "#", "Target", "Mode", "IP", "Protocol", "URL Rating", "Domain Rating",
    "Ahrefs Rank", "Organic / Total Keywords", "Organic / Keywords (Top 3)",
    "Organic / Keywords (4-10)", "Organic / Keywords (11-20)",
    "Organic / Keywords (21-50)", "Organic / Keywords (51+)",
    "Organic / Traffic", "Organic / Value", "Organic / Top Countries",
    "Paid / Keywords", "Paid / Ads", "Paid / Traffic", "Paid / Cost",
    "Ref. domains / All", "Ref. domains / Followed", "Ref. domains / Not followed",
    "Ref. IPs / IPs", "Ref. IPs / Subnets", "Backlinks / All",
    "Backlinks / Followed", "Backlinks / Not followed", "Backlinks / Redirects",
    "Backlinks / Internal", "Outgoing domains / Followed",
    "Outgoing domains / All time", "Outgoing links / Followed",
    "Outgoing links / All time",
]

# §2.1 Fields that must be present as columns; their absence is a validation error.
REQUIRED_COLUMNS = [
    "Target",
    "Domain Rating",
    "Ref. domains / All",
    "Ref. domains / Followed",
    "Backlinks / All",
]

# Columns treated as numeric metrics ("" -> 0, floats allowed).
NUMERIC_COLUMNS = [
    "URL Rating", "Domain Rating", "Ahrefs Rank", "Organic / Total Keywords",
    "Organic / Keywords (Top 3)", "Organic / Keywords (4-10)",
    "Organic / Keywords (11-20)", "Organic / Keywords (21-50)",
    "Organic / Keywords (51+)", "Organic / Traffic", "Organic / Value",
    "Paid / Keywords", "Paid / Ads", "Paid / Traffic", "Paid / Cost",
    "Ref. domains / All", "Ref. domains / Followed", "Ref. domains / Not followed",
    "Ref. IPs / IPs", "Ref. IPs / Subnets", "Backlinks / All",
    "Backlinks / Followed", "Backlinks / Not followed", "Backlinks / Redirects",
    "Backlinks / Internal", "Outgoing domains / Followed",
    "Outgoing domains / All time", "Outgoing links / Followed",
    "Outgoing links / All time",
]

_TOP_COUNTRY_RE = re.compile(r"^\(([a-z]{2}),\s*(\d+)\)")
_TLD_STRIP_SCHEME_RE = re.compile(r"^[a-z]+://", re.IGNORECASE)


def to_number(value) -> float:
    """§3.1: coerce a metric cell to a float.

    Empty string / None / non-numeric -> 0. Decimal separator is a dot; there
    are no thousands separators in the export.
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s == "":
        return 0.0
    # Strip stray characters that occasionally sneak into exports (spaces used
    # as grouping, non-breaking spaces). Keep sign, digits, dot.
    s = s.replace(" ", "").replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_top_countries(value) -> tuple[Optional[str], Optional[int]]:
    """§3.2: parse ``"(cc, N)"`` -> (cc lowercase, N).

    Empty / unparseable -> (None, None), i.e. a domain with no organic.
    """
    if value is None:
        return None, None
    s = str(value).strip()
    if s == "":
        return None, None
    m = _TOP_COUNTRY_RE.match(s.lower())
    if not m:
        return None, None
    return m.group(1), int(m.group(2))


def parse_tld(target) -> Optional[str]:
    """§3.3: extract everything after the first dot of the host.

    ``handfie.com/`` -> ``com``; ``diariodelsur.com.co/`` -> ``com.co``;
    ``transparencia.utea.edu.pe/`` -> ``utea.edu.pe``.
    """
    if target is None:
        return None
    s = str(target).strip().lower()
    if s == "":
        return None
    s = _TLD_STRIP_SCHEME_RE.sub("", s)
    host = s.split("/", 1)[0]  # drop path
    host = host.split("?", 1)[0]
    if "." not in host:
        return None
    return host.split(".", 1)[1] or None


def normalize_target(target) -> str:
    """Canonical Target string (kept verbatim in output, only trimmed)."""
    return "" if target is None else str(target).strip()


def is_data_row(row: dict) -> bool:
    """§11: reject total/header rows that slip into the input.

    A real data row has a non-empty Target and a numeric ``#`` (if ``#`` is
    present at all).
    """
    target = normalize_target(row.get("Target"))
    if target == "":
        return False
    if "#" in row:
        hash_val = str(row.get("#", "")).strip()
        if hash_val != "" and not hash_val.lstrip("-").isdigit():
            return False
    return True
