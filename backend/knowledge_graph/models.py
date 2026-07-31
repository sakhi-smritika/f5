"""In-memory shapes for graph reads used by the pipeline and agents."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str
    graph_id: str
    label: str
    description: str | None = None
    user_interest: float = 0.0
    kbit_count: int = 0
    last_expanded_at: str | None = None


@dataclass
class GraphSnapshot:
    """A graph with its nodes and adjacency, loaded for one invoke run."""

    id: str
    title: str
    description: str | None
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)
    neighbors: dict[str, list[GraphNode]] = field(default_factory=dict)

    def node_by_id(self, node_id: str) -> GraphNode | None:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def labels_for_nodes(self, node_ids: list[str]) -> list[str]:
        by_id = {node.id: node.label for node in self.nodes}
        return [by_id[nid] for nid in node_ids if nid in by_id]
