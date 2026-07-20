"""HTTP API for config defaults, validation and presets (§9)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..ahrefs.config import merge_with_defaults, validate_config
from ..config_defaults import default_config

router = APIRouter(prefix="/api/config", tags=["config"])


class ValidatePayload(BaseModel):
    config: dict | None = None


class SavePresetPayload(BaseModel):
    name: str
    config: dict


@router.get("/default")
async def get_default():
    return {"config": default_config()}


@router.post("/validate")
async def validate(payload: ValidatePayload):
    """Merge onto defaults and return warnings (weights ≥ 0, tiers monotone)."""
    cfg = merge_with_defaults(payload.config)
    return {"config": cfg, "warnings": validate_config(cfg)}


@router.get("/presets")
async def list_presets(request: Request):
    return {"presets": request.app.state.presets.list_names()}


@router.post("/presets")
async def save_preset(request: Request, payload: SavePresetPayload):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Имя пресета не может быть пустым.")
    request.app.state.presets.save(name, merge_with_defaults(payload.config))
    return {"ok": True, "name": name}


@router.get("/presets/{name}")
async def get_preset(request: Request, name: str):
    cfg = request.app.state.presets.get(name)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Пресет не найден.")
    return {"name": name, "config": cfg}


@router.delete("/presets/{name}")
async def delete_preset(request: Request, name: str):
    request.app.state.presets.delete(name)
    return {"ok": True}
