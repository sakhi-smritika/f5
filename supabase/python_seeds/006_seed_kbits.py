"""
Seed knowledge bits into public.knowledge_bits, plus optional discussion threads.

Each bit is keyed by user email + title for idempotency. ``goal_name`` optionally
links a bit to a seeded goal (resolved to ``related_goal``); run 004_seed_goals
first when using it. ``graph_link`` resolves graph and node UUIDs from
005_seed_knowledge_graphs and writes full ``metadata`` plus ``knowledge_bit_nodes``
rows.

When a bit carries a ``comments`` list, we also seed a discussion thread for it,
mirroring 002_seed_conversations: a ``conversations`` row linked to the bit via
``kbit_id`` plus an ADK session, then the LlmAgent + Runner replays each user
comment so the agent persists both the comment and its reply.

The discussion flow only runs when at least one bit has comments, so seeding
bits without comments needs neither ``OPENAI_API_KEY`` nor ``DATABASE_URL``.
"""

import asyncio
import logging
import os
import uuid
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types as genai_types

from .data.conversations import APP_NAME, DEFAULT_MODEL
from .data.kbits import SEED_KBITS
from .utils import get_admin_client, resolve_user_ids_by_emails

logger = logging.getLogger(__name__)

INTERACTION_FIELDS = (
    "is_read",
    "is_viewed",
    "is_liked",
    "is_disliked",
    "rating",
    "is_marked_relavant",
    "is_marked_irrelavant",
)


def resolve_goal_id(
    supabase: Any, *, user_id: str, goal_name: str
) -> str | None:
    response = (
        supabase.table("goals")
        .select("id")
        .eq("user_id", user_id)
        .eq("goal_name", goal_name)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return str(rows[0]["id"]) if rows else None


def load_graph_registry(
    supabase: Any, user_ids_by_email: dict[str, str]
) -> dict[tuple[str, str], dict]:
    """Map (email, graph_title) -> {id, title, nodes: {label: node_id}}."""
    registry: dict[tuple[str, str], dict] = {}
    for email, user_id in user_ids_by_email.items():
        graphs = (
            supabase.table("knowledge_graphs")
            .select("id, title")
            .eq("user_id", user_id)
            .execute()
        )
        for graph in getattr(graphs, "data", None) or []:
            graph_id = str(graph["id"])
            title = graph["title"]
            nodes = (
                supabase.table("knowledge_nodes")
                .select("id, label, kbit_count")
                .eq("graph_id", graph_id)
                .execute()
            )
            node_map = {
                row["label"]: str(row["id"])
                for row in (getattr(nodes, "data", None) or [])
            }
            registry[(email, title)] = {
                "id": graph_id,
                "title": title,
                "nodes": node_map,
            }
    return registry


def resolve_metadata(
    entry: dict,
    *,
    email: str,
    registry: dict[tuple[str, str], dict],
) -> dict | None:
    """Merge seed metadata with resolved graph and expansion node ids."""
    base = dict(entry.get("metadata") or {})
    graph_link = entry.get("graph_link")
    if not graph_link:
        return base or None

    graph_title = graph_link["graph_title"]
    graph = registry.get((email, graph_title))
    if not graph:
        logger.warning(
            "Graph '%s' not found for %s; metadata will omit graph fields. "
            "Run 005_seed_knowledge_graphs first.",
            graph_title,
            email,
        )
        return base or None

    expansion_label = graph_link["expansion_node_label"]
    expansion_id = graph["nodes"].get(expansion_label)
    if not expansion_id:
        logger.warning(
            "Node '%s' not found in graph '%s' for %s",
            expansion_label,
            graph_title,
            email,
        )
        return base or None

    base["graph"] = {"id": graph["id"], "title": graph["title"]}
    base["expansion_node"] = {"id": expansion_id, "label": expansion_label}
    return base


def resolve_node_ids(
    entry: dict,
    *,
    email: str,
    registry: dict[tuple[str, str], dict],
) -> list[str]:
    graph_link = entry.get("graph_link")
    if not graph_link:
        return []

    graph = registry.get((email, graph_link["graph_title"]))
    if not graph:
        return []

    ids: list[str] = []
    for label in graph_link.get("node_labels") or []:
        node_id = graph["nodes"].get(label)
        if node_id:
            ids.append(node_id)
        else:
            logger.warning(
                "Node '%s' not found in graph '%s' for %s",
                label,
                graph_link["graph_title"],
                email,
            )
    return ids


def link_bit_to_nodes(
    supabase: Any, *, kbit_id: str, node_ids: list[str]
) -> None:
    for node_id in node_ids:
        existing = (
            supabase.table("knowledge_bit_nodes")
            .select("kbit_id")
            .eq("kbit_id", kbit_id)
            .eq("node_id", node_id)
            .limit(1)
            .execute()
        )
        rows = getattr(existing, "data", None) or []
        if rows:
            continue
        supabase.table("knowledge_bit_nodes").insert(
            {"kbit_id": kbit_id, "node_id": node_id}
        ).execute()


def mark_expansion_node(supabase: Any, node_id: str) -> None:
    response = (
        supabase.table("knowledge_nodes")
        .select("kbit_count")
        .eq("id", node_id)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    current = int(rows[0].get("kbit_count") or 0) if rows else 0
    supabase.table("knowledge_nodes").update(
        {"kbit_count": current + 1}
    ).eq("id", node_id).execute()


def find_existing_kbit(
    supabase: Any, *, user_id: str, title: str
) -> dict | None:
    response = (
        supabase.table("knowledge_bits")
        .select("id, generator_prompt, metadata")
        .eq("user_id", user_id)
        .eq("title", title)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return rows[0] if rows else None


def build_kbit_row(
    user_id: str,
    entry: dict,
    *,
    related_goal: str | None,
    metadata: dict | None,
) -> dict:
    row = {
        "user_id": user_id,
        "title": entry["title"],
        "content": entry["content"],
        "related_goal": related_goal,
    }
    for field in INTERACTION_FIELDS:
        if field in entry:
            row[field] = entry[field]
    if "generator_prompt" in entry:
        row["generator_prompt"] = entry["generator_prompt"]
    if metadata:
        row["metadata"] = metadata
    return row


def apply_graph_links(
    supabase: Any,
    *,
    kbit_id: str,
    entry: dict,
    email: str,
    registry: dict[tuple[str, str], dict],
    bump_expansion: bool = False,
) -> None:
    node_ids = resolve_node_ids(entry, email=email, registry=registry)
    if not node_ids:
        return
    link_bit_to_nodes(supabase, kbit_id=kbit_id, node_ids=node_ids)
    if not bump_expansion:
        return
    graph_link = entry["graph_link"]
    graph = registry.get((email, graph_link["graph_title"]))
    if not graph:
        return
    expansion_id = graph["nodes"].get(graph_link["expansion_node_label"])
    if expansion_id:
        mark_expansion_node(supabase, expansion_id)


# --- Discussion seeding -----------------------------------------------------


def get_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in environment")
    return api_key


def get_session_service() -> DatabaseSessionService:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required to seed knowledge-bit discussion threads."
        )
    return DatabaseSessionService(db_url=database_url)


def build_kbit_agent(api_key: str, *, title: str, content: str) -> LlmAgent:
    instruction = (
        "You are Smritika, discussing one specific Knowledge Bit with the user in "
        "a threaded comment section. The bit below is the subject of this "
        "conversation: ground every reply in it, help the user reflect on it and "
        "apply it to their life and goals, and keep replies warm and concise. Do "
        "not repeat the bit verbatim; build on it.\n\n"
        f"Knowledge Bit title: {title}\n"
        f"Knowledge Bit content:\n{content}"
    )
    return LlmAgent(
        model=LiteLlm(model=DEFAULT_MODEL, api_key=api_key),
        name="assistant",
        instruction=instruction,
        tools=[],
    )


def discussion_exists(supabase: Any, *, kbit_id: str) -> bool:
    response = (
        supabase.table("conversations")
        .select("id")
        .eq("kbit_id", kbit_id)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return bool(rows)


def create_discussion(
    supabase: Any, *, user_id: str, kbit_id: str, title: str
) -> str:
    conversation_id = str(uuid.uuid4())
    supabase.table("conversations").insert(
        {
            "id": conversation_id,
            "user_id": user_id,
            "title": title,
            "kbit_id": kbit_id,
        }
    ).execute()
    return conversation_id


async def seed_discussions(discussions: list[dict]) -> None:
    supabase = get_admin_client()
    api_key = get_openai_api_key()
    session_service = get_session_service()
    await session_service.prepare_tables()

    for disc in discussions:
        kbit_id = disc["kbit_id"]
        user_id = disc["user_id"]
        title = disc["title"]
        content = disc["content"]
        comments = disc["comments"]

        if discussion_exists(supabase, kbit_id=kbit_id):
            print(f"↺ Discussion already exists for kbit: {title}")
            continue

        conversation_id = create_discussion(
            supabase, user_id=user_id, kbit_id=kbit_id, title=title
        )
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=conversation_id
        )

        runner = Runner(
            agent=build_kbit_agent(api_key, title=title, content=content),
            app_name=APP_NAME,
            session_service=session_service,
        )

        for comment in comments:
            new_message = genai_types.Content(
                role="user", parts=[genai_types.Part(text=comment)]
            )
            async for _event in runner.run_async(
                user_id=user_id,
                session_id=conversation_id,
                new_message=new_message,
                run_config=RunConfig(),
            ):
                pass

        print(
            f"✓ Seeded discussion for kbit '{title}' with {len(comments)} comment(s)"
        )


def seed_kbits() -> None:
    """Seed knowledge bits (idempotent by user + title) and their discussions."""
    supabase = get_admin_client()
    emails = sorted({entry["email"] for entry in SEED_KBITS})
    user_ids_by_email = resolve_user_ids_by_emails(supabase, emails)

    missing = [email for email in emails if email not in user_ids_by_email]
    if missing:
        raise RuntimeError(
            "Cannot seed knowledge bits; run 001_seed_users first. Missing users: "
            + ", ".join(missing)
        )

    graph_registry = load_graph_registry(supabase, user_ids_by_email)
    logger.info("Seeding %s knowledge bit(s)...", len(SEED_KBITS))

    discussions: list[dict] = []

    for entry in SEED_KBITS:
        email = entry["email"]
        user_id = user_ids_by_email[email]
        title = entry["title"]
        metadata = resolve_metadata(entry, email=email, registry=graph_registry)

        existing = find_existing_kbit(supabase, user_id=user_id, title=title)
        if existing:
            kbit_id = str(existing["id"])
            logger.info("↺ Knowledge bit already exists for %s: %s", email, title)
            prompt = entry.get("generator_prompt")
            if prompt and not existing.get("generator_prompt"):
                supabase.table("knowledge_bits").update(
                    {"generator_prompt": prompt}
                ).eq("id", kbit_id).execute()
                logger.info("  ↻ Backfilled generator_prompt for: %s", title)
            if metadata and not existing.get("metadata"):
                supabase.table("knowledge_bits").update(
                    {"metadata": metadata}
                ).eq("id", kbit_id).execute()
                logger.info("  ↻ Backfilled metadata for: %s", title)
            if entry.get("graph_link"):
                apply_graph_links(
                    supabase,
                    kbit_id=kbit_id,
                    entry=entry,
                    email=email,
                    registry=graph_registry,
                )
        else:
            related_goal = None
            goal_name = entry.get("goal_name")
            if goal_name:
                related_goal = resolve_goal_id(
                    supabase, user_id=user_id, goal_name=goal_name
                )
                if not related_goal:
                    logger.warning(
                        "Goal '%s' not found for %s; seeding bit '%s' as goalless. "
                        "Run 004_seed_goals first to link it.",
                        goal_name,
                        email,
                        title,
                    )

            row = build_kbit_row(
                user_id, entry, related_goal=related_goal, metadata=metadata
            )
            response = supabase.table("knowledge_bits").insert(row).execute()
            rows = getattr(response, "data", None) or []
            if not rows:
                raise RuntimeError(
                    f"Failed to insert knowledge bit '{title}' for {email}"
                )
            kbit_id = str(rows[0]["id"])
            logger.info("✓ Seeded knowledge bit for %s: %s", email, title)
            if entry.get("graph_link"):
                apply_graph_links(
                    supabase,
                    kbit_id=kbit_id,
                    entry=entry,
                    email=email,
                    registry=graph_registry,
                    bump_expansion=True,
                )

        comments = entry.get("comments")
        if comments:
            discussions.append(
                {
                    "kbit_id": kbit_id,
                    "user_id": user_id,
                    "title": title,
                    "content": entry["content"],
                    "comments": comments,
                }
            )

    if discussions:
        logger.info(
            "Seeding %s knowledge-bit discussion(s) via the agent runner...",
            len(discussions),
        )
        asyncio.run(seed_discussions(discussions))

    logger.info("Knowledge bit seeding complete!")


if __name__ == "__main__":
    seed_kbits()
