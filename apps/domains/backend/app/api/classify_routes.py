"""HTTP API for the name classifier (Part 2)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ..classifier import export
from ..classifier.normalize import parse_input

router = APIRouter(prefix="/api/classify", tags=["classify"])


class PreviewPayload(BaseModel):
    text: str


class RunPayload(BaseModel):
    text: str
    ignore_cache: bool = False


class ExportPayload(BaseModel):
    format: str = "csv"          # csv | txt
    bucket: str | None = None    # good | bad | review | None(all)


def _store(request: Request):
    return request.app.state.classifier_store


@router.post("/preview")
async def preview(payload: PreviewPayload):
    """UI-1: recognized / duplicates / invalid counts, no run."""
    p = parse_input(payload.text)
    return {
        "recognized": p.recognized,
        "valid": len(p.domains),
        "duplicates": p.duplicates,
        "invalid": len(p.invalid),
    }


@router.post("/runs")
async def start_run(request: Request, payload: RunPayload):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Пустой список доменов.")
    run_id = request.app.state.run_manager.start(
        _store(request), payload.text, payload.ignore_cache
    )
    return {"run_id": run_id}


def _run_view(request: Request, run_id: str, with_results: bool = True) -> dict:
    store = _store(request)
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Прогон не найден.")
    view = {"run": run}
    if with_results:
        results = store.get_results(run_id)
        buckets = {"good": [], "bad": [], "review": []}
        for r in results:
            buckets.setdefault(r["bucket"], []).append(r)
        view["buckets"] = buckets
    return view


@router.get("/runs/{run_id}")
async def get_run(request: Request, run_id: str):
    """UI-2/3: poll progress + incremental buckets."""
    return _run_view(request, run_id)


@router.post("/runs/{run_id}/cancel")
async def cancel_run(request: Request, run_id: str):
    ok = request.app.state.run_manager.request_cancel(run_id)
    return {"cancelled": ok}


@router.get("/runs")
async def list_runs(request: Request):
    """UI-11: run history."""
    return {"runs": _store(request).list_runs()}


@router.get("/runs/{run_id}/logs")
async def get_logs(request: Request, run_id: str):
    """UI-12: logs for a run."""
    return {"logs": _store(request).get_logs(run_id)}


@router.post("/runs/{run_id}/export")
async def export_run(request: Request, run_id: str, payload: ExportPayload):
    results = _store(request).get_results(run_id)
    if payload.bucket:
        results = [r for r in results if r["bucket"] == payload.bucket]
    if payload.format == "txt":
        body, media, ext = export.to_txt(results), "text/plain", "txt"
    else:
        body, media, ext = export.to_csv(results), "text/csv", "csv"
    name = payload.bucket or "all"
    return PlainTextResponse(
        body, media_type=media,
        headers={"Content-Disposition": f'attachment; filename="classify_{name}.{ext}"'},
    )
