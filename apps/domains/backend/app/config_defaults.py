"""Default configuration for the Ahrefs quantitative domain filter.

Mirrors §9 of the TZ exactly. Every number here is a *default*; all of them
are overridable from the UI. The pipeline is a pure function of (rows, config),
so changing any of these recomputes results without re-uploading data.
"""

from __future__ import annotations

# The canonical default config. Kept as a plain dict so it round-trips cleanly
# to JSON for the frontend and to YAML/JSON presets on disk.
DEFAULT_CONFIG: dict = {
    "reject": {
        # Correction 1а: mandatory DR floor — reject anything under dr_min.
        # Default 0.5 kills DR=0 (and near-zero) domains that slip past
        # dead/thin because they carry ~30 followed ref.domains.
        "dr_floor": {"dr_min": 0.5},
        "dead": {"dr_eq": 0, "rd_fol_eq": 0},
        "spam_blast": {
            "rd_fol_eq": 0,
            "bl_rd_min": 0.9,
            "bl_rd_max": 1.4,
            "rd_all_min": 100,
        },
        "thin": {"rd_fol_max": 3, "dr_max": 2},
        "burn_hacked": {"burn_min": 1000, "dr_max": 15, "org_eq": 0},
        # Correction 1б: optional — same spam breed at DR 1-2. Off by default.
        "spam_floor_reject": {
            "enabled": False,
            "fol_share_max": 0.15,
            "bl_rd_max": 1.3,
            "org_eq": 0,
        },
    },
    "score": {
        "weights": {
            "dr": 0.45,
            "rd_fol": 0.20,
            "subnets": 0.12,
            "org": 0.13,
            "spam_pen": 0.10,
        },
        "caps": {"dr": 40, "rd_fol": 300, "subnets": 400, "org": 2000},
        "spam_pen": {"bl_rd_base": 1, "cap": 20},
    },
    "tiers": {
        "A_min": 55,
        "B_min": 40,
        "C_min": 28,
        # score < C_min -> Review
    },
    "flags": {
        "spam_floor": {
            "rd_all_min": 200,
            "rd_all_max": 320,
            "fol_share_max": 0.35,
            "org_eq": 0,
        },
        "burn": {"burn_min": 500},
        "geo": {
            "allowlist": [],  # e.g. ["au"]; empty => flag_geo_review not set
        },
        "cjk": {
            "set": ["cn", "jp", "kr", "tw", "hk", "mo"],
            "action": "review",  # review | reject | flag_only
        },
    },
}


def default_config() -> dict:
    """Return a deep copy of the default config."""
    import copy

    return copy.deepcopy(DEFAULT_CONFIG)
