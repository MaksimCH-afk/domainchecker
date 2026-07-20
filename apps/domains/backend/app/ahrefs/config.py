"""Config merge & validation (§9 of the TZ).

The UI edits any subset of the config; we deep-merge it onto the defaults and
validate. Validation surfaces *warnings* (never a silent failure): weights must
be >= 0 and tier bounds must be monotone (A_min >= B_min >= C_min).
"""

from __future__ import annotations

import copy

from ..config_defaults import default_config


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` onto a copy of ``base``."""
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def merge_with_defaults(partial: dict | None) -> dict:
    """Fill any missing keys from defaults so the pipeline always has them."""
    return deep_merge(default_config(), partial or {})


def validate_config(cfg: dict) -> list[str]:
    """Return a list of human-readable warnings (empty == valid)."""
    warnings: list[str] = []

    # weights >= 0
    for name, val in cfg["score"]["weights"].items():
        if val < 0:
            warnings.append(f"Вес score.weights.{name} < 0 ({val}); веса должны быть ≥ 0.")

    # caps > 0 (log-normalization divides by ln(1+cap))
    for name, val in cfg["score"]["caps"].items():
        if val <= 0:
            warnings.append(f"Константа score.caps.{name} должна быть > 0 (сейчас {val}).")

    # tiers monotone: A_min >= B_min >= C_min
    t = cfg["tiers"]
    if not (t["A_min"] >= t["B_min"] >= t["C_min"]):
        warnings.append(
            f"Границы тиров не монотонны: требуется A_min ≥ B_min ≥ C_min, "
            f"сейчас A={t['A_min']}, B={t['B_min']}, C={t['C_min']}."
        )

    # cjk.action must be a known value
    action = cfg["flags"]["cjk"].get("action")
    if action not in ("review", "reject", "flag_only"):
        warnings.append(
            f"flags.cjk.action='{action}' неизвестно; допустимо review|reject|flag_only."
        )

    return warnings
