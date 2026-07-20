"""HTTP API for the Ahrefs quantitative filter (Part 1)."""

from __future__ import annotations

from fastapi import APIRouter, Body, File, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ..ahrefs import export, loader
from ..ahrefs.config import merge_with_defaults, validate_config
from ..ahrefs.pipeline import analyze

router = APIRouter(prefix="/api/ahrefs", tags=["ahrefs"])


class RowsPayload(BaseModel):
    rows: list[dict]
    headers: list[str] | None = None


class AnalyzePayload(BaseModel):
    config: dict | None = None


class ExportPayload(BaseModel):
    config: dict | None = None
    format: str = "csv"          # csv | txt
    include_raw: bool = False    # §10 passthrough toggle


def _stats(load: loader.LoadResult) -> dict:
    return {
        "recognized": len(load.records),
        "total_rows": load.total_rows,
        "duplicates_removed": load.duplicates_removed,
    }


@router.post("/datasets")
async def upload_dataset(request: Request, file: UploadFile = File(...)):
    """§2: accept an Ahrefs export file (either UTF-16/tab or UTF-8/comma)."""
    data = await file.read()
    try:
        load = loader.parse_file(data)
    except loader.LoadError as e:
        raise HTTPException(status_code=422, detail=str(e))
    ds = request.app.state.datasets.add(load)
    return {"dataset_id": ds.id, "filename": file.filename, **_stats(load)}


@router.post("/datasets/rows")
async def upload_rows(request: Request, payload: RowsPayload):
    """§2 alt: host app supplies already-loaded rows directly (no file)."""
    try:
        load = loader.parse_rows(payload.rows, payload.headers)
    except loader.LoadError as e:
        raise HTTPException(status_code=422, detail=str(e))
    ds = request.app.state.datasets.add(load)
    return {"dataset_id": ds.id, **_stats(load)}


def _run(request: Request, dataset_id: str, config: dict | None):
    ds = request.app.state.datasets.get(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Датасет не найден (истёк или неверный id).")
    cfg = merge_with_defaults(config)
    warnings = validate_config(cfg)
    rows, summary = analyze(ds.records, cfg)
    summary["duplicates_removed"] = ds.duplicates_removed
    summary["total_input_rows"] = ds.total_rows
    return ds, cfg, warnings, rows, summary


@router.post("/datasets/{dataset_id}/analyze")
async def analyze_dataset(request: Request, dataset_id: str, payload: AnalyzePayload):
    """§9: recompute score/tiers/flags on already-loaded data for a given config."""
    _, _, warnings, rows, summary = _run(request, dataset_id, payload.config)
    return {
        "summary": summary,
        "warnings": warnings,
        "rows": [r.to_dict() for r in rows],
    }


@router.post("/datasets/{dataset_id}/export")
async def export_dataset(request: Request, dataset_id: str, payload: ExportPayload):
    """§10: export result as CSV or TXT."""
    _, _, _, rows, _ = _run(request, dataset_id, payload.config)
    if payload.format == "txt":
        body = export.to_txt(rows, include_raw=payload.include_raw)
        media = "text/plain"
        ext = "txt"
    else:
        body = export.to_csv(rows, include_raw=payload.include_raw)
        media = "text/csv"
        ext = "csv"
    return PlainTextResponse(
        body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="ahrefs_filter.{ext}"'},
    )


@router.post("/datasets/{dataset_id}/targets")
async def bridge_targets(
    request: Request,
    dataset_id: str,
    payload: AnalyzePayload = Body(default=AnalyzePayload()),
    tiers: str = "A,B,C",
):
    """Bridge to Part 2: return the Targets in the selected tiers, ready to
    feed the name classifier. The two TZ halves are one pipeline — this is the
    hand-off point (quantitative gate -> name gate)."""
    _, _, _, rows, _ = _run(request, dataset_id, payload.config)
    wanted = {t.strip() for t in tiers.split(",") if t.strip()}
    targets = [r.target for r in rows if r.tier in wanted]
    return {"count": len(targets), "targets": targets, "tiers": sorted(wanted)}
