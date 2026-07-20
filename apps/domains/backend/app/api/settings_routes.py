"""HTTP API for classifier AI/run settings (§3.2 of TZ-2).

Keys are stored server-side and masked on read (NFR-4)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..classifier.providers import PROVIDER_BASE_URLS
from ..classifier.settings_defaults import masked_settings

router = APIRouter(prefix="/api/classify/settings", tags=["classify-settings"])


class SettingsPatch(BaseModel):
    # Any subset of settings; api_keys accepts {provider: key}, blanks ignored.
    data: dict


def _store(request: Request):
    return request.app.state.classifier_store


@router.get("")
async def get_settings(request: Request):
    store = _store(request)
    settings = store.get_settings()
    return {
        "settings": masked_settings(settings, store.has_keys()),
        "provider_base_urls": PROVIDER_BASE_URLS,
    }


@router.put("")
async def update_settings(request: Request, payload: SettingsPatch):
    store = _store(request)
    settings = store.save_settings(dict(payload.data))
    return {"settings": masked_settings(settings, store.has_keys())}
