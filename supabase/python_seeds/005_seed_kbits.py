"""
Seed knowledge bits into public.knowledge_bits.

Each bit is keyed by user email + title for idempotency. ``goal_name`` optionally
links a bit to a seeded goal (resolved to ``related_goal``); run 004_seed_goals
first when using it. Interaction flags fall back to the table defaults.
"""

import logging
from typing import Any

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


def seed_kbits() -> None:
    """Seed knowledge bits for configured users (idempotent by user + title)."""
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

    for entry in SEED_KBITS:
        email = entry["email"]
        user_id = user_ids_by_email[email]
        title = entry["title"]

        if find_existing_kbit_id(supabase, user_id=user_id, title=title):
            logger.info("↺ Knowledge bit already exists for %s: %s", email, title)
            continue

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
        logger.info("✓ Seeded knowledge bit for %s: %s", email, title)

    logger.info("Knowledge bit seeding complete!")


if __name__ == "__main__":
    seed_kbits()
