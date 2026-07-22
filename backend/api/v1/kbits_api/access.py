"""Ownership checks and read-only Supabase queries for knowledge bits.

Reads go through the service-role client but are always scoped by ``user_id`` so
one user can never touch another user's bits. Handlers call these helpers before
mutating a row.
"""

from fastapi import HTTPException, status

from config.supabase import get_supabase_service_client

from .constants import RECENT_TITLES_LIMIT

# Columns returned to the client. ``user_id`` is intentionally omitted.
KBIT_COLUMNS = (
    "id, created_at, updated_at, title, content, related_goal, is_read, "
    "is_liked, is_disliked, rating, is_marked_relavant, is_marked_irrelavant"
)


def get_owned_kbit(kbit_id: str, user_id: str) -> dict:
    """Fetch a knowledge bit, enforcing ownership. Raises 404 otherwise."""
    client = get_supabase_service_client()
    result = (
        client.table("knowledge_bits")
        .select(KBIT_COLUMNS)
        .eq("id", kbit_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge bit not found"
        )
    return rows[0]


def list_kbits(
    user_id: str,
    *,
    is_read: bool | None = None,
    related_goal: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Return the user's bits, newest first, with optional filters."""
    query = (
        get_supabase_service_client()
        .table("knowledge_bits")
        .select(KBIT_COLUMNS)
        .eq("user_id", user_id)
    )
    if is_read is not None:
        query = query.eq("is_read", is_read)
    if related_goal:
        query = query.eq("related_goal", related_goal)

    result = (
        query.order("created_at", desc=True)
        .range(offset, offset + max(1, limit) - 1)
        .execute()
    )
    return result.data or []


def fetch_recent_titles(user_id: str, limit: int = RECENT_TITLES_LIMIT) -> list[str]:
    """Return recent bit titles for dedup / query-exclusion (redundancy avoidance)."""
    result = (
        get_supabase_service_client()
        .table("knowledge_bits")
        .select("title")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [row["title"] for row in (result.data or []) if row.get("title")]
