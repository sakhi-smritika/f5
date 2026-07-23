"""
Seed knowledge bits into public.knowledge_bits, plus optional discussion threads.

Each bit is keyed by user email + title for idempotency. ``goal_name`` optionally
links a bit to a seeded goal (resolved to ``related_goal``); run 004_seed_goals
first when using it. Interaction flags fall back to the table defaults.

When a bit carries a ``comments`` list, we also seed a discussion thread for it,
mirroring 002_seed_conversations: a ``conversations`` row linked to the bit via
``kbit_id`` plus an ADK session, then the LlmAgent + Runner replays each user
comment so the agent persists both the comment and its reply. The bit itself is
injected into the agent's instruction (never stored as a message), matching the
runtime behaviour in ``agent.agent``.

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

# Interaction flags copied straight through when present in a seed entry.
INTERACTION_FIELDS = (
    "is_read",
    "is_liked",
    "is_disliked",
    "rating",
    "is_marked_relavant",
    "is_marked_irrelavant",
)


def resolve_goal_id(
    supabase: Any, *, user_id: str, goal_name: str
) -> str | None:
    """Return the id of a user's goal by name, or None if it doesn't exist."""
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


def find_existing_kbit_id(
    supabase: Any, *, user_id: str, title: str
) -> str | None:
    response = (
        supabase.table("knowledge_bits")
        .select("id")
        .eq("user_id", user_id)
        .eq("title", title)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return str(rows[0]["id"]) if rows else None


def build_kbit_row(
    user_id: str, entry: dict, *, related_goal: str | None
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
    return row


# --- Discussion (comment thread) seeding via the ADK runner -----------------


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
    """Build an agent whose instruction embeds the bit under discussion.

    This mirrors the discussion framing that ``agent.agent`` injects at runtime,
    so seeded replies read the same as live ones.
    """
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
    """Create a discussion conversation row linked to a bit."""
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
    """Replay each bit's comments through the agent runner (idempotent by kbit)."""
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


# --- Entry point ------------------------------------------------------------


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

    logger.info("Seeding %s knowledge bit(s)...", len(SEED_KBITS))

    # Discussions are collected and seeded after all bits exist, so the agent
    # runner is only spun up once (and only when there are comments to seed).
    discussions: list[dict] = []

    for entry in SEED_KBITS:
        email = entry["email"]
        user_id = user_ids_by_email[email]
        title = entry["title"]

        kbit_id = find_existing_kbit_id(supabase, user_id=user_id, title=title)
        if kbit_id:
            logger.info("↺ Knowledge bit already exists for %s: %s", email, title)
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

            row = build_kbit_row(user_id, entry, related_goal=related_goal)
            response = supabase.table("knowledge_bits").insert(row).execute()
            rows = getattr(response, "data", None) or []
            if not rows:
                raise RuntimeError(
                    f"Failed to insert knowledge bit '{title}' for {email}"
                )
            kbit_id = str(rows[0]["id"])
            logger.info("✓ Seeded knowledge bit for %s: %s", email, title)

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
