"""File loader for Ahrefs Batch Analysis exports (§2 of the TZ).

Ahrefs ships the *same* export in two shapes — UTF-16/tab and UTF-8/comma.
Per §2 this "bridge" layer normalizes both to one header-keyed set of rows so
the pure pipeline downstream never has to care about the file format. Field
mapping is by header name, not index.

This layer also owns the load-time validation & dedup of §11.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from .metrics import DomainRecord
from .parsing import REQUIRED_COLUMNS, is_data_row, normalize_target


class LoadError(ValueError):
    """Raised on a validation failure that must not be silently swallowed."""


@dataclass
class LoadResult:
    records: list[DomainRecord]
    total_rows: int          # data rows seen (post total/header filtering)
    duplicates_removed: int
    headers: list[str]


def _decode(data: bytes) -> str:
    """Decode either Ahrefs shape to text."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    # UTF-8 (with or without BOM).
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Last resort so a single odd byte never aborts a whole upload.
        return data.decode("latin-1")


def _sniff_delimiter(first_line: str) -> str:
    """Tab for the UTF-16 shape, comma for the UTF-8 shape."""
    if first_line.count("\t") >= first_line.count(","):
        return "\t"
    return ","


def parse_file(data: bytes) -> LoadResult:
    """Parse raw upload bytes into normalized, deduped records."""
    text = _decode(data)
    if not text.strip():
        raise LoadError("Файл пустой: не найдено ни одной строки.")

    first_line = text.splitlines()[0]
    delimiter = _sniff_delimiter(first_line)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    headers = [h.strip() for h in (reader.fieldnames or [])]

    return _build_result(reader, headers)


def parse_rows(rows: list[dict], headers: list[str] | None = None) -> LoadResult:
    """Parse already-loaded dict rows (host app supplies rows directly, §2)."""
    if headers is None:
        headers = list(rows[0].keys()) if rows else []
    return _build_result(iter(rows), [h.strip() for h in headers])


def _build_result(row_iter, headers: list[str]) -> LoadResult:
    # §2.1 required columns must be present (as columns).
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise LoadError(
            "Во входных данных нет обязательных колонок: "
            + ", ".join(missing)
            + ". Проверьте, что загружена выгрузка Ahrefs Batch Analysis."
        )

    seen: set[str] = set()
    records: list[DomainRecord] = []
    total_rows = 0
    duplicates = 0

    for row in row_iter:
        # Normalize header whitespace so header-name mapping is exact.
        clean = {(k.strip() if isinstance(k, str) else k): v for k, v in row.items()}
        if not is_data_row(clean):  # §11: skip total/header rows
            continue
        total_rows += 1
        target = normalize_target(clean.get("Target"))
        if target in seen:  # §11: dedup by Target, keep first
            duplicates += 1
            continue
        seen.add(target)
        records.append(DomainRecord.from_row(clean))

    if not records:
        raise LoadError("Не найдено ни одной валидной строки с доменом.")

    return LoadResult(
        records=records,
        total_rows=total_rows,
        duplicates_removed=duplicates,
        headers=headers,
    )
