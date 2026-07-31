"""Supabase reads and writes for knowledge graphs."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from config.supabase import get_supabase_service_client

from .models import GraphNode, GraphSnapshot

logger = logging.getLogger(__name__)

_GRAPH_COLUMNS = "id, title, description"
_NODE_COLUMNS = (
    "id, graph_id, label, description, user_interest, kbit_count, last_expanded_at"
)
_EDGE_COLUMNS = "source_id, target_id"


def list_user_graphs(user_id: str) -> list[dict]:
    result = (
        get_supabase_service_client()
        .table("knowledge_graphs")
        .select(_GRAPH_COLUMNS)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def count_user_graphs(user_id: str) -> int:
    return len(list_user_graphs(user_id))


def load_graph_snapshot(graph_id: str, user_id: str) -> GraphSnapshot | None:
    """Load one graph with nodes and adjacency, scoped to the owner."""
    client = get_supabase_service_client()
    graph_result = (
        client.table("knowledge_graphs")
        .select(_GRAPH_COLUMNS)
        .eq("id", graph_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = graph_result.data or []
    if not rows:
        return None

    graph = rows[0]
    node_rows = (
        client.table("knowledge_nodes")
        .select(_NODE_COLUMNS)
        .eq("graph_id", graph_id)
        .execute()
    ).data or []
    edge_rows = (
        client.table("knowledge_edges")
        .select(_EDGE_COLUMNS)
        .eq("graph_id", graph_id)
        .execute()
    ).data or []

    nodes = [_node_from_row(row) for row in node_rows]
    edges = [(row["source_id"], row["target_id"]) for row in edge_rows]
    neighbors = _build_neighbors(nodes, edges)

    return GraphSnapshot(
        id=graph["id"],
        title=graph["title"],
        description=graph.get("description"),
        nodes=nodes,
        edges=edges,
        neighbors=neighbors,
    )


def upsert_node(
    graph_id: str,
    label: str,
    *,
    description: str | None = None,
) -> GraphNode:
    """Find or create a node by label within a graph."""
    client = get_supabase_service_client()
    normalized = label.strip()
    existing = (
        client.table("knowledge_nodes")
        .select(_NODE_COLUMNS)
        .eq("graph_id", graph_id)
        .ilike("label", normalized)
        .limit(1)
        .execute()
    ).data or []
    if existing:
        return _node_from_row(existing[0])

    row = {
        "id": str(uuid.uuid4()),
        "graph_id": graph_id,
        "label": normalized,
        "description": description,
    }
    inserted = (
        client.table("knowledge_nodes").insert(row).select(_NODE_COLUMNS).execute()
    ).data or [row]
    return _node_from_row(inserted[0])


def upsert_edge(graph_id: str, source_id: str, target_id: str) -> None:
    """Insert an undirected edge using canonical node ordering."""
    if source_id == target_id:
        return
    low, high = sorted((source_id, target_id))
    client = get_supabase_service_client()
    existing = (
        client.table("knowledge_edges")
        .select("id")
        .eq("graph_id", graph_id)
        .eq("source_id", low)
        .eq("target_id", high)
        .limit(1)
        .execute()
    ).data
    if existing:
        return
    client.table("knowledge_edges").insert(
        {
            "id": str(uuid.uuid4()),
            "graph_id": graph_id,
            "source_id": low,
            "target_id": high,
        }
    ).execute()


def mark_node_expanded(node_id: str, *, increment_kbit_count: int = 1) -> None:
    client = get_supabase_service_client()
    current = (
        client.table("knowledge_nodes")
        .select("kbit_count")
        .eq("id", node_id)
        .limit(1)
        .execute()
    ).data or [{"kbit_count": 0}]
    client.table("knowledge_nodes").update(
        {
            "kbit_count": int(current[0].get("kbit_count") or 0) + increment_kbit_count,
            "last_expanded_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", node_id).execute()


def link_bit_to_nodes(kbit_id: str, node_ids: list[str]) -> None:
    if not node_ids:
        return
    rows = [{"kbit_id": kbit_id, "node_id": node_id} for node_id in node_ids]
    get_supabase_service_client().table("knowledge_bit_nodes").insert(rows).execute()


def patch_bit_metadata(kbit_id: str, metadata: dict) -> None:
    get_supabase_service_client().table("knowledge_bits").update(
        {"metadata": metadata}
    ).eq("id", kbit_id).execute()


def _node_from_row(row: dict) -> GraphNode:
    return GraphNode(
        id=row["id"],
        graph_id=row["graph_id"],
        label=row["label"],
        description=row.get("description"),
        user_interest=float(row.get("user_interest") or 0),
        kbit_count=int(row.get("kbit_count") or 0),
        last_expanded_at=row.get("last_expanded_at"),
    )


def _build_neighbors(
    nodes: list[GraphNode], edges: list[tuple[str, str]]
) -> dict[str, list[GraphNode]]:
    by_id = {node.id: node for node in nodes}
    neighbors: dict[str, list[GraphNode]] = {node.id: [] for node in nodes}
    for source_id, target_id in edges:
        source = by_id.get(source_id)
        target = by_id.get(target_id)
        if source and target:
            neighbors[source_id].append(target)
            neighbors[target_id].append(source)
    return neighbors
