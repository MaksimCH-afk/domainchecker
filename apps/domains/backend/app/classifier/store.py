"""SQLite persistence for the classifier (FR-12, FR-13, NFR-2, DEP-3).

Tables: settings (key-value), runs, results, logs, cache. Everything lives on
the mounted /data volume so history/logs/cache survive restarts. Results and
logs are written incrementally per batch so a crash never loses finished work.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

from .settings_defaults import DEFAULT_SETTINGS


class ClassifierStore:
    def __init__(self, db_path: str) -> None:
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    created_at REAL, finished_at REAL,
                    status TEXT,                 -- running|done|cancelled|error
                    provider TEXT, model TEXT, batch_api INTEGER,
                    total INTEGER, processed INTEGER,
                    good INTEGER, bad INTEGER, review INTEGER, errors INTEGER,
                    prompt_tokens INTEGER, completion_tokens INTEGER,
                    est_cost REAL
                );
                CREATE TABLE IF NOT EXISTS results (
                    run_id TEXT, domain TEXT, original TEXT, bucket TEXT,
                    verdict TEXT, category TEXT, name_language TEXT,
                    is_english_name INTEGER, confidence REAL,
                    matched_terms TEXT, reason TEXT,
                    PRIMARY KEY (run_id, domain)
                );
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT, ts REAL, level TEXT, message TEXT
                );
                CREATE TABLE IF NOT EXISTS cache (
                    domain TEXT PRIMARY KEY,
                    verdict TEXT, category TEXT, name_language TEXT,
                    is_english_name INTEGER, confidence REAL,
                    matched_terms TEXT, reason TEXT, updated_at REAL
                );
                """
            )

    # --- settings (kv) -----------------------------------------------------
    def get_settings(self) -> dict:
        with self._lock, self._conn() as c:
            row = c.execute("SELECT value FROM kv WHERE key='settings'").fetchone()
            keys_row = c.execute("SELECT value FROM kv WHERE key='api_keys'").fetchone()
        settings = dict(DEFAULT_SETTINGS)
        if row:
            settings.update(json.loads(row["value"]))
        settings["api_keys"] = json.loads(keys_row["value"]) if keys_row else {}
        return settings

    def save_settings(self, patch: dict) -> dict:
        current = self.get_settings()
        api_keys = current.get("api_keys", {})
        # API keys are updated only when a non-empty value is provided (so the
        # UI can send blanks to leave existing keys untouched).
        incoming_keys = patch.pop("api_keys", None)
        if isinstance(incoming_keys, dict):
            for k, v in incoming_keys.items():
                if v:
                    api_keys[k] = v
        merged = {k: v for k, v in current.items() if k != "api_keys"}
        merged.update({k: v for k, v in patch.items() if k != "api_keys"})
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO kv(key,value) VALUES('settings',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (json.dumps(merged),),
            )
            c.execute(
                "INSERT INTO kv(key,value) VALUES('api_keys',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (json.dumps(api_keys),),
            )
        return self.get_settings()

    def has_keys(self) -> dict[str, bool]:
        keys = self.get_settings().get("api_keys", {})
        return {k: bool(v) for k, v in keys.items()}

    # --- runs --------------------------------------------------------------
    def create_run(self, run_id: str, total: int, provider: str, model: str,
                   batch_api: bool) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO runs(id,created_at,status,provider,model,batch_api,"
                "total,processed,good,bad,review,errors,prompt_tokens,"
                "completion_tokens,est_cost) VALUES(?,?,?,?,?,?,?,0,0,0,0,0,0,0,0)",
                (run_id, time.time(), "running", provider, model,
                 1 if batch_api else 0, total),
            )

    def update_run(self, run_id: str, **fields) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        with self._lock, self._conn() as c:
            c.execute(f"UPDATE runs SET {cols} WHERE id=?",
                      (*fields.values(), run_id))

    def get_run(self, run_id: str) -> dict | None:
        with self._lock, self._conn() as c:
            row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def list_runs(self, limit: int = 50) -> list[dict]:
        with self._lock, self._conn() as c:
            rows = c.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # --- results (incremental) --------------------------------------------
    def add_results(self, run_id: str, rows: list[dict]) -> None:
        with self._lock, self._conn() as c:
            c.executemany(
                "INSERT OR REPLACE INTO results(run_id,domain,original,bucket,"
                "verdict,category,name_language,is_english_name,confidence,"
                "matched_terms,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                [
                    (run_id, r["domain"], r["original"], r["bucket"], r["verdict"],
                     r["category"], r["name_language"], 1 if r["is_english_name"] else 0,
                     r["confidence"], json.dumps(r["matched_terms"]), r["reason"])
                    for r in rows
                ],
            )

    def get_results(self, run_id: str) -> list[dict]:
        with self._lock, self._conn() as c:
            rows = c.execute(
                "SELECT * FROM results WHERE run_id=?", (run_id,)
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["is_english_name"] = bool(d["is_english_name"])
            d["matched_terms"] = json.loads(d["matched_terms"] or "[]")
            out.append(d)
        return out

    # --- logs --------------------------------------------------------------
    def log(self, run_id: str, level: str, message: str) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO logs(run_id,ts,level,message) VALUES(?,?,?,?)",
                (run_id, time.time(), level, message),
            )

    def get_logs(self, run_id: str) -> list[dict]:
        with self._lock, self._conn() as c:
            rows = c.execute(
                "SELECT ts,level,message FROM logs WHERE run_id=? ORDER BY id", (run_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    # --- cache (FR-12) -----------------------------------------------------
    def cache_get(self, domains: list[str]) -> dict[str, dict]:
        if not domains:
            return {}
        placeholders = ",".join("?" * len(domains))
        with self._lock, self._conn() as c:
            rows = c.execute(
                f"SELECT * FROM cache WHERE domain IN ({placeholders})", domains
            ).fetchall()
        out = {}
        for r in rows:
            d = dict(r)
            d["is_english_name"] = bool(d["is_english_name"])
            d["matched_terms"] = json.loads(d["matched_terms"] or "[]")
            out[d["domain"]] = d
        return out

    def cache_put(self, rows: list[dict]) -> None:
        with self._lock, self._conn() as c:
            c.executemany(
                "INSERT OR REPLACE INTO cache(domain,verdict,category,name_language,"
                "is_english_name,confidence,matched_terms,reason,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                [
                    (r["domain"], r["verdict"], r["category"], r["name_language"],
                     1 if r["is_english_name"] else 0, r["confidence"],
                     json.dumps(r["matched_terms"]), r["reason"], time.time())
                    for r in rows if r["verdict"] != "error"
                ],
            )
