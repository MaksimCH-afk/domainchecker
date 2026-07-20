"""FastAPI entrypoint for the `domains` module of monopanel.

One app, one process, one panel. Both halves of the pipeline mount here and
share the same DB file, yet neither core imports the other — Part 1 (Ahrefs
quantitative filter) and Part 2 (name classifier) are each fully usable on
their own; the Ahrefs→classifier bridge is an optional one-way handoff of a
plain domain list.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import ahrefs_routes, classify_routes, config_routes, settings_routes
from .classifier.engine import RunManager
from .classifier.store import ClassifierStore
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
app.state.classifier_store = ClassifierStore(DB_PATH)
app.state.run_manager = RunManager()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "module": "domains"}


# Part 1: Ahrefs quantitative filter.
app.include_router(ahrefs_routes.router)
app.include_router(config_routes.router)
# Part 2: name classifier.
app.include_router(classify_routes.router)
app.include_router(settings_routes.router)
