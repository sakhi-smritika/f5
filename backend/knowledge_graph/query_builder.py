"""Build a ``Query`` from a selected graph expansion node."""

from __future__ import annotations

from api.v1.kbits_api.pipeline.base import PipelineContext, Query
from knowledge_graph.models import GraphNode, GraphSnapshot


def build_graph_query(
    snapshot: GraphSnapshot,
    node: GraphNode,
    ctx: PipelineContext,
) -> Query:
    """Turn an expansion node and its neighborhood into a generator query."""
    neighbors = snapshot.neighbors.get(node.id, [])
    neighbor_labels = [n.label for n in neighbors[:5]]

    include = [node.label, *neighbor_labels[:3]]
    covered = {node.label, *neighbor_labels}
    exclude = [
        *ctx.existing_titles,
        *[label for label in covered if label != node.label],
    ]

    frontier = (
        f"Expand the concept '{node.label}' in the '{snapshot.title}' knowledge graph. "
        f"The user already has {node.kbit_count} bit(s) on this node. "
        f"Neighboring concepts: {', '.join(neighbor_labels) or 'none yet'}. "
        "Seek concrete, adjacent ideas not yet covered."
    )

    ctx.selected_graph_id = snapshot.id
    ctx.selected_node_id = node.id

    return Query(
        include=include,
        exclude=exclude,
        brief=frontier,
        graph_id=snapshot.id,
        expansion_node_id=node.id,
    )
