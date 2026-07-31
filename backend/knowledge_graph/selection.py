"""Weighted graph and node selection for graph query strategies."""

from __future__ import annotations

from .weights import pick_weighted

from .models import GraphNode, GraphSnapshot
from .scoring import score_node


def pick_graph(
    graph_weights: dict[str, float], user_graphs: list[dict]
) -> dict | None:
    """Pick one graph by weight. Equal weight when none configured."""
    if not user_graphs:
        return None

    valid_ids = {graph["id"] for graph in user_graphs}
    pool = {
        graph_id: weight
        for graph_id, weight in graph_weights.items()
        if graph_id in valid_ids and weight > 0
    }
    if not pool:
        pool = {graph["id"]: 1.0 for graph in user_graphs}

    picked_id = pick_weighted(pool)
    if picked_id is None:
        return user_graphs[0]
    return next((g for g in user_graphs if g["id"] == picked_id), user_graphs[0])


def pick_node_by_potential(snapshot: GraphSnapshot) -> GraphNode | None:
    """Return the node with the highest generation-potential score."""
    if not snapshot.nodes:
        return None

    best: GraphNode | None = None
    best_score = float("-inf")
    for node in snapshot.nodes:
        neighbor_count = len(snapshot.neighbors.get(node.id, []))
        node_score = score_node(node, neighbor_count)
        if node_score > best_score:
            best_score = node_score
            best = node
    return best
