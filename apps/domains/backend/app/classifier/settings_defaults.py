"""Default AI/run settings for the name classifier (§3.2, §5.2 of TZ-2).

Keys are stored server-side (§2.1) and masked on read (NFR-4). API keys are
never returned in full and never written to logs/history.
"""

from __future__ import annotations

DEFAULT_SETTINGS: dict = {
    "provider": "openai",              # openai | openrouter | mock (offline demo)
    "model": "gpt-4.1-mini",           # recommended default (Correction 2)
    "base_url": "",                    # optional override for OpenAI-compatible
    "batch_api": False,                # Batch API (−50%) — factored into cost
    "temperature": 0.2,
    "batch_size": 50,                  # FR-5
    "concurrency": 4,                  # FR-8
    "max_retries": 3,                  # FR-8
    # Correction 1: confidence no longer gates the bucket (reference only).
    "price_in_per_1k": 0.0,            # NFR-3 (user fills per active model)
    "price_out_per_1k": 0.0,
    # api_keys are stored separately and never serialized back to the client.
}

# Recommended classifier model + reserves for the settings dropdown
# (Correction 5 / Correction 2). Flagships/Pro are intentionally excluded.
CLASSIFIER_MODELS = [
    {"id": "gpt-4.1-mini", "label": "gpt-4.1-mini — рекомендуется", "recommended": True},
    {"id": "gpt-4.1-nano", "label": "gpt-4.1-nano — дешевле (~×4)", "recommended": False},
    {"id": "gpt-5.4-mini", "label": "gpt-5.4-mini — резерв, точнее", "recommended": False},
    {"id": "gpt-5.4-nano", "label": "gpt-5.4-nano — резерв", "recommended": False},
]

# Keys that hold secrets and must never be returned to the client in full.
SECRET_KEYS = {"openai", "openrouter"}


def masked_settings(settings: dict, has_keys: dict[str, bool]) -> dict:
    """Return settings safe to send to the UI: secrets replaced by a flag."""
    safe = {k: v for k, v in settings.items() if k != "api_keys"}
    safe["api_keys_set"] = has_keys
    return safe
