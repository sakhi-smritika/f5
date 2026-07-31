"""
Seed knowledge graphs, nodes, and edges.

Run after 001_seed_users and before 006_seed_kbits. Graphs are idempotent by
user email + title; nodes by graph + label.
"""

import logging
from typing import Any

from .data.knowledge_graphs import SEED_KNOWLEDGE_GRAPHS
from .utils import get_admin_client, resolve_user_ids_by_emails

logger = logging.getLogger(__name__)


def find_existing_graph(
    supabase: Any, *, user_id: str, title: str
) -> dict | None:
    response = (
        supabase.table("knowledge_graphs")
        .select("id, title")
        .eq("user_id", user_id)
        .eq("title", title)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return rows[0] if rows else None


def find_existing_node(
    supabase: Any, *, graph_id: str, label: str
) -> dict | None:
    response = (
        supabase.table("knowledge_nodes")
        .select("id, label, kbit_count")
        .eq("graph_id", graph_id)
        .eq("label", label)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return rows[0] if rows else None


def upsert_edge(
    supabase: Any, *, graph_id: str, source_id: str, target_id: str
) -> None:
    low, high = sorted((source_id, target_id))
    existing = (
        supabase.table("knowledge_edges")
        .select("id")
        .eq("graph_id", graph_id)
        .eq("source_id", low)
        .eq("target_id", high)
        .limit(1)
        .execute()
    )
    rows = getattr(existing, "data", None) or []
    if rows:
        return
    supabase.table("knowledge_edges").insert(
        {
            "graph_id": graph_id,
            "source_id": low,
            "target_id": high,
        }
    ).execute()


def seed_knowledge_graphs() -> None:
    supabase = get_admin_client()
    emails = sorted({entry["email"] for entry in SEED_KNOWLEDGE_GRAPHS})
    user_ids_by_email = resolve_user_ids_by_emails(supabase, emails)

    missing = [email for email in emails if email not in user_ids_by_email]
    if missing:
        raise RuntimeError(
            "Cannot seed knowledge graphs; run 001_seed_users first. Missing: "
            + ", ".join(missing)
        )

    logger.info("Seeding %s knowledge graph(s)...", len(SEED_KNOWLEDGE_GRAPHS))

    for entry in SEED_KNOWLEDGE_GRAPHS:
        email = entry["email"]
        user_id = user_ids_by_email[email]
        title = entry["title"]

        existing_graph = find_existing_graph(supabase, user_id=user_id, title=title)
        if existing_graph:
            graph_id = str(existing_graph["id"])
            logger.info("↺ Knowledge graph already exists for %s: %s", email, title)
        else:
            response = (
                supabase.table("knowledge_graphs")
                .insert(
                    {
                        "user_id": user_id,
                        "title": title,
                        "description": entry.get("description"),
                    }
                )
                .execute()
            )
            rows = getattr(response, "data", None) or []
            if not rows:
                raise RuntimeError(f"Failed to insert knowledge graph '{title}'")
            graph_id = str(rows[0]["id"])
            logger.info("✓ Seeded knowledge graph for %s: %s", email, title)

        node_ids_by_key: dict[str, str] = {}

        for node in entry.get("nodes") or []:
            label = node["label"]
            existing_node = find_existing_node(
                supabase, graph_id=graph_id, label=label
            )
            if existing_node:
                node_ids_by_key[node["key"]] = str(existing_node["id"])
                logger.info("  ↺ Node already exists: %s", label)
                continue

            row = {
                "graph_id": graph_id,
                "label": label,
                "description": node.get("description"),
            }
            response = supabase.table("knowledge_nodes").insert(row).execute()
            rows = getattr(response, "data", None) or []
            if not rows:
                raise RuntimeError(f"Failed to insert node '{label}'")
            node_ids_by_key[node["key"]] = str(rows[0]["id"])
            logger.info("  ✓ Seeded node: %s", label)

        for source_key, target_key in entry.get("edges") or []:
            upsert_edge(
                supabase,
                graph_id=graph_id,
                source_id=node_ids_by_key[source_key],
                target_id=node_ids_by_key[target_key],
            )

    logger.info("Knowledge graph seeding complete!")


if __name__ == "__main__":
    seed_knowledge_graphs()
