"""Read-only ADK tools for knowledge-graph exploration."""

from __future__ import annotations

from tools.context import require_user_id

from knowledge_graph.store import list_user_graphs, load_graph_snapshot


def list_my_knowledge_graphs() -> list[dict]:
    """List the signed-in user's knowledge graphs (id, title, description)."""
    user_id = require_user_id()
    return list_user_graphs(user_id)


def get_knowledge_graph(graph_id: str) -> dict:
    """Return one knowledge graph with its nodes and edges.

    Args:
        graph_id: UUID of the graph to load.
    """
    user_id = require_user_id()
    snapshot = load_graph_snapshot(graph_id, user_id)
    if snapshot is None:
        return {"error": "Graph not found"}
    return {
        "id": snapshot.id,
        "title": snapshot.title,
        "description": snapshot.description,
        "nodes": [
            {
                "id": node.id,
                "label": node.label,
                "kbit_count": node.kbit_count,
                "user_interest": node.user_interest,
            }
            for node in snapshot.nodes
        ],
        "edges": [
            {"source_id": source, "target_id": target}
            for source, target in snapshot.edges
        ],
    }


def list_graph_nodes(graph_id: str) -> list[dict]:
    """List concept nodes in a knowledge graph.

    Args:
        graph_id: UUID of the graph.
    """
    user_id = require_user_id()
    snapshot = load_graph_snapshot(graph_id, user_id)
    if snapshot is None:
        return []
    return [
        {
            "id": node.id,
            "label": node.label,
            "description": node.description,
            "kbit_count": node.kbit_count,
            "user_interest": node.user_interest,
        }
        for node in snapshot.nodes
    ]


def get_node_neighbors(node_id: str) -> list[dict]:
    """Return nodes directly connected to the given node."""
    user_id = require_user_id()
    for graph in list_user_graphs(user_id):
        snapshot = load_graph_snapshot(graph["id"], user_id)
        if snapshot is None:
            continue
        if snapshot.node_by_id(node_id) is None:
            continue
        return [
            {"id": n.id, "label": n.label, "kbit_count": n.kbit_count}
            for n in snapshot.neighbors.get(node_id, [])
        ]
    return []


def list_node_kbits(node_id: str, limit: int = 10) -> list[dict]:
    """Return knowledge bits linked to a concept node.

    Args:
        node_id: UUID of the concept node.
        limit: Maximum rows to return (default 10).
    """
    from config.supabase import get_supabase_service_client

    user_id = require_user_id()
    client = get_supabase_service_client()
    links = (
        client.table("knowledge_bit_nodes")
        .select("kbit_id")
        .eq("node_id", node_id)
        .limit(max(1, min(limit, 50)))
        .execute()
    ).data or []
    if not links:
        return []

    kbit_ids = [row["kbit_id"] for row in links]
    bits = (
        client.table("knowledge_bits")
        .select("id, title, content, is_liked, is_disliked, rating")
        .eq("user_id", user_id)
        .in_("id", kbit_ids)
        .execute()
    ).data or []
    return bits
