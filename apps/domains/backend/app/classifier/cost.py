"""Cost estimation (NFR-3 of TZ-2). Price per 1K tokens comes from settings;
Batch API applies a −50% discount."""

from __future__ import annotations


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    price_in_per_1k: float,
    price_out_per_1k: float,
    batch_api: bool,
) -> float:
    cost = (prompt_tokens / 1000.0) * price_in_per_1k
    cost += (completion_tokens / 1000.0) * price_out_per_1k
    if batch_api:
        cost *= 0.5
    return round(cost, 6)
