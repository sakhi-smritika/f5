"""
Seed goals into public.goals.

Supports root goals and sub-goals via parent_key references in the seed data.
"""

import logging
from typing import Any

from .data.goals import SEED_GOALS
from .utils import get_admin_client, resolve_user_ids_by_emails

logger = logging.getLogger(__name__)


def find_existing_goal_id(
    supabase: Any,
    *,
    user_id: str,
    goal_name: str,
    parent_goal_id: str | None,
) -> str | None:
    query = (
        supabase.table("goals")
        .select("id")
        .eq("user_id", user_id)
        .eq("goal_name", goal_name)
    )
    if parent_goal_id:
        query = query.eq("parent_goal", parent_goal_id)
    else:
        query = query.is_("parent_goal", "null")

    response = query.limit(1).execute()
    rows = getattr(response, "data", None) or []
    if not rows:
        return None
    return str(rows[0]["id"])


def build_goal_row(
    user_id: str,
    entry: dict,
    *,
    parent_goal_id: str | None,
) -> dict:
    return {
        "user_id": user_id,
        "goal_name": entry["goal_name"],
        "goal_description": entry.get("goal_description"),
        "progress": entry.get("progress"),
        "parent_goal": parent_goal_id,
    }


def seed_goals() -> None:
    """Seed root and child goals for configured users."""
    supabase = get_admin_client()
    emails = sorted({entry["email"] for entry in SEED_GOALS})
    user_ids_by_email = resolve_user_ids_by_emails(supabase, emails)

    missing = [email for email in emails if email not in user_ids_by_email]
    if missing:
        raise RuntimeError(
            "Cannot seed goals; run 001_seed_users first. Missing users: "
            + ", ".join(missing)
        )

    goal_ids_by_key: dict[tuple[str, str], str] = {}
    logger.info("Seeding %s goal(s)...", len(SEED_GOALS))

    for entry in SEED_GOALS:
        email = entry["email"]
        user_id = user_ids_by_email[email]
        key = entry["key"]
        parent_key = entry.get("parent_key")

        parent_goal_id = None
        if parent_key:
            parent_goal_id = goal_ids_by_key.get((email, parent_key))
            if not parent_goal_id:
                raise RuntimeError(
                    f"Parent goal '{parent_key}' must be seeded before child '{key}' for {email}"
                )

        existing_id = find_existing_goal_id(
            supabase,
            user_id=user_id,
            goal_name=entry["goal_name"],
            parent_goal_id=parent_goal_id,
        )
        if existing_id:
            goal_ids_by_key[(email, key)] = existing_id
            logger.info(
                "↺ Goal already exists for %s: %s",
                email,
                entry["goal_name"],
            )
            continue

        row = build_goal_row(user_id, entry, parent_goal_id=parent_goal_id)
        response = supabase.table("goals").insert(row).execute()
        rows = getattr(response, "data", None) or []
        if not rows:
            raise RuntimeError(f"Failed to insert goal '{entry['goal_name']}' for {email}")

        goal_id = str(rows[0]["id"])
        goal_ids_by_key[(email, key)] = goal_id
        logger.info("✓ Seeded goal for %s: %s", email, entry["goal_name"])

    logger.info("Goal seeding complete!")


if __name__ == "__main__":
    seed_goals()
