"""FastAPI entrypoint for the `domains` module of monopanel.

Part 1 (Ahrefs quantitative filter) is wired up here. Part 2 (name classifier)
will mount its own router alongside these under the same app / same panel.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import ahrefs_routes, config_routes
from .store import DatasetStore, PresetStore

DB_PATH = os.environ.get("DOMAINS_DB_PATH", "./data/domains.db")

app = FastAPI(title="monopanel · domains", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # panel is self-hosted; tighten via reverse proxy
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize stores eagerly so state exists for every request (incl. tests).
app.state.datasets = DatasetStore()
app.state.presets = PresetStore(DB_PATH)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "module": "domains"}


app.include_router(ahrefs_routes.router)
app.include_router(config_routes.router)
