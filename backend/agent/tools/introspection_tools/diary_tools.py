"""
Read-only tools over the user's diary (``public.diary``).

Every function is scoped to the signed-in user via ``require_user_id()`` and
reads through the service-role Supabase client. Functions return plain,
JSON-serializable dicts so ADK can hand the result back to the model.
"""

from config.supabase import get_supabase_service_client

from ..context import require_user_id

# Columns exposed to the assistant. `id`/`user_id` are intentionally omitted.
_ENTRY_COLUMNS = (
    "date, how_was_the_day, major_events, general_content, day_log, updated_at"
)


def get_diary_entry(date: str) -> dict:
    """Get the full diary entry for a specific day.

    Args:
        date: The day to fetch, in ISO ``YYYY-MM-DD`` format.

    Returns:
        The diary entry for that date, including ``how_was_the_day``,
        ``major_events``, ``general_content`` and the hourly ``day_log``. If no
        entry exists, ``found`` is ``False``.
    """
    user_id = require_user_id()
    result = (
        get_supabase_service_client()
        .table("diary")
        .select(_ENTRY_COLUMNS)
        .eq("user_id", user_id)
        .eq("date", date)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return {"found": False, "date": date}
    return {"found": True, "entry": rows[0]}


def get_recent_diary_entries(limit: int = 7) -> dict:
    """List the user's most recent diary entries, newest first.

    Args:
        limit: Maximum number of entries to return (1-30). Defaults to 7.

    Returns:
        A dict with ``count`` and a list of ``entries`` ordered by date
        descending.
    """
    safe_limit = max(1, min(int(limit), 30))
    user_id = require_user_id()
    result = (
        get_supabase_service_client()
        .table("diary")
        .select(_ENTRY_COLUMNS)
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(safe_limit)
        .execute()
    )
    entries = result.data or []
    return {"count": len(entries), "entries": entries}


def search_diary(keyword: str) -> dict:
    """Search the user's diary for a keyword.

    Matches (case-insensitive) against the reflection, major events and general
    text of each entry.

    Args:
        keyword: The text to search for.

    Returns:
        A dict with ``count`` and matching ``entries`` (newest first).
    """
    term = (keyword or "").strip()
    if not term:
        return {"count": 0, "entries": [], "note": "Empty keyword."}

    user_id = require_user_id()
    # Inside a PostgREST `or` filter, ilike uses `*` (not `%`) as the wildcard,
    # and commas separate conditions, so strip commas from the term.
    pattern = "*" + term.replace(",", " ") + "*"
    or_filter = (
        f"how_was_the_day.ilike.{pattern},"
        f"major_events.ilike.{pattern},"
        f"general_content.ilike.{pattern}"
    )
    result = (
        get_supabase_service_client()
        .table("diary")
        .select(_ENTRY_COLUMNS)
        .eq("user_id", user_id)
        .or_(or_filter)
        .order("date", desc=True)
        .limit(20)
        .execute()
    )
    entries = result.data or []
    return {"count": len(entries), "entries": entries}


def get_day_log(date: str) -> dict:
    """Get the hourly day log for a specific day.

    Args:
        date: The day to fetch, in ISO ``YYYY-MM-DD`` format.

    Returns:
        A dict with the ``day_log`` object (hourly slots keyed ``"0"``..``"23"``)
        for that date, or ``found`` ``False`` if there is no entry.
    """
    user_id = require_user_id()
    result = (
        get_supabase_service_client()
        .table("diary")
        .select("date, day_log")
        .eq("user_id", user_id)
        .eq("date", date)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return {"found": False, "date": date}
    return {"found": True, "date": date, "day_log": rows[0].get("day_log") or {}}
