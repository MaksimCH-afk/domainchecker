"""In-memory dataset store + SQLite-backed config presets.

Parsed datasets live in memory for the session: the pipeline is a pure,
cheap function, so "recompute on config change without re-upload" (§9) is just
re-running `analyze` against the retained `DomainRecord`s.

Config presets (§9: save/load a profile per niche/geo, reset to defaults) are
persisted to SQLite so they survive restarts on a Docker volume.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .ahrefs.loader import LoadResult
from .ahrefs.metrics import DomainRecord


@dataclass
class Dataset:
    id: str
    records: list[DomainRecord]
    total_rows: int
    duplicates_removed: int
    headers: list[str]
    created_at: float


class DatasetStore:
    """Session-scoped store of parsed datasets (in memory)."""

    def __init__(self, max_datasets: int = 32) -> None:
        self._data: dict[str, Dataset] = {}
        self._lock = threading.Lock()
        self._max = max_datasets

    def add(self, load: LoadResult) -> Dataset:
        ds = Dataset(
            id=uuid.uuid4().hex,
            records=load.records,
            total_rows=load.total_rows,
            duplicates_removed=load.duplicates_removed,
            headers=load.headers,
            created_at=time.time(),
        )
        with self._lock:
            self._data[ds.id] = ds
            # Evict oldest if over capacity.
            if len(self._data) > self._max:
                oldest = min(self._data.values(), key=lambda d: d.created_at)
                self._data.pop(oldest.id, None)
        return ds

    def get(self, dataset_id: str) -> Dataset | None:
        with self._lock:
            return self._data.get(dataset_id)


class PresetStore:
    """SQLite store for named config presets and the active settings."""

    def __init__(self, db_path: str) -> None:
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS presets (
                    name        TEXT PRIMARY KEY,
                    config_json TEXT NOT NULL,
                    updated_at  REAL NOT NULL
                )
                """
            )

    def save(self, name: str, config: dict) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO presets(name, config_json, updated_at) VALUES(?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET config_json=excluded.config_json, "
                "updated_at=excluded.updated_at",
                (name, json.dumps(config), time.time()),
            )

    def get(self, name: str) -> dict | None:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT config_json FROM presets WHERE name=?", (name,)
            ).fetchone()
        return json.loads(row["config_json"]) if row else None

    def list_names(self) -> list[str]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT name FROM presets ORDER BY updated_at DESC"
            ).fetchall()
        return [r["name"] for r in rows]

    def delete(self, name: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("DELETE FROM presets WHERE name=?", (name,))
