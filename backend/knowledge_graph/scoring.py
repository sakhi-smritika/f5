"""Generation-potential scoring for knowledge-graph nodes."""

from __future__ import annotations

from .models import GraphNode


def score_node(node: GraphNode, neighbor_count: int) -> float:
    """Score a node for expansion priority.

    Higher is better. Favours frontier nodes (few edges), user interest,
    and nodes not recently or heavily covered by bits.
    """
    frontier = max(0, 5 - neighbor_count) / 5.0
    coverage_penalty = min(node.kbit_count, 5) / 5.0
    recency_penalty = 0.2 if node.last_expanded_at else 0.0
    return (
        1.0 * frontier
        + 0.5 * node.user_interest
        - 0.8 * coverage_penalty
        - 0.3 * recency_penalty
    )
