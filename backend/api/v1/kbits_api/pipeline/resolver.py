"""Weighted-random strategy resolution for the kbits pipeline."""

from __future__ import annotations

from knowledge_graph.constants import GRAPH_QUERY_STRATEGIES
from knowledge_graph.weights import normalize_weights, pick_weighted

from .base import Registry

__all__ = [
    "GRAPH_QUERY_STRATEGIES",
    "normalize_weights",
    "pick_weighted",
    "resolve_stage_strategy",
]


def resolve_stage_strategy(
    registry: Registry,
    explicit: str | None,
    user_weights: dict[str, float] | None,
    *,
    exclude: set[str] | None = None,
) -> str:
    """Pick a registered strategy by explicit override or weighted random."""
    if explicit:
        return explicit

    if not user_weights:
        return registry.default or registry.names()[0]

    pool = dict(user_weights)
    if exclude:
        pool = {name: weight for name, weight in pool.items() if name not in exclude}

    registered = set(registry.names())
    pool = {name: weight for name, weight in pool.items() if name in registered}

    if not pool:
        options = [name for name in registry.names() if name not in (exclude or set())]
        if not options:
            return registry.default or registry.names()[0]
        pool = {name: 1.0 for name in options}

    picked = pick_weighted(pool)
    if picked and picked in registry._items:
        return picked
    return registry.default or registry.names()[0]
