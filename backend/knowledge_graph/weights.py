"""Weighted random selection shared by strategy and graph pickers."""

from __future__ import annotations

import random


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Drop non-positive weights and scale to sum 1."""
    filtered = {key: float(value) for key, value in weights.items() if float(value) > 0}
    total = sum(filtered.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in filtered.items()}


def pick_weighted(weights: dict[str, float]) -> str | None:
    """Return one key chosen by normalized weight, or ``None`` when empty."""
    normalized = normalize_weights(weights)
    if not normalized:
        return None

    threshold = random.random()
    cumulative = 0.0
    last_key: str | None = None
    for key, weight in normalized.items():
        cumulative += weight
        last_key = key
        if threshold <= cumulative:
            return key
    return last_key
