"""
Tools over the user's diary (``public.diary``).

Every function is scoped to the signed-in user via ``require_user_id()`` and
goes through the service-role Supabase client. Functions return plain,
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


def upsert_diary_entry(
    date: str,
    how_was_the_day: str | None = None,
    major_events: str | None = None,
    general_content: str | None = None,
) -> dict:
    """Create or update the user's diary entry for a specific day.

    Only the fields you pass are written; omitted fields are left unchanged on an
    existing entry. This does not touch the hourly ``day_log`` (use
    ``set_day_log_hour`` for that). Confirm with the user before recording
    reflections on their behalf.

    Args:
        date: The day to write, in ISO ``YYYY-MM-DD`` format. Required.
        how_was_the_day: The user's overall reflection for the day.
        major_events: Notable events of the day.
        general_content: Any other free-form journal text for the day.

    Returns:
        ``{"ok": True, "entry": {...}}`` with the saved entry, or
        ``{"ok": False, "error": "..."}`` if the date is missing or nothing was
        provided to write.
    """
    clean_date = (date or "").strip()
    if not clean_date:
        return {"ok": False, "error": "date is required (YYYY-MM-DD)."}

    updates: dict = {}
    if how_was_the_day is not None:
        updates["how_was_the_day"] = how_was_the_day
    if major_events is not None:
        updates["major_events"] = major_events
    if general_content is not None:
        updates["general_content"] = general_content

    if not updates:
        return {"ok": False, "error": "Nothing to write; provide at least one field."}

    user_id = require_user_id()
    payload = {"user_id": user_id, "date": clean_date, **updates}
    try:
        result = (
            get_supabase_service_client()
            .table("diary")
            .upsert(payload, on_conflict="user_id,date")
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 - surface a structured error to the model
        return {"ok": False, "error": f"Failed to save diary entry: {exc}"}

    rows = result.data or []
    return {"ok": True, "entry": rows[0] if rows else payload}


def set_day_log_hour(date: str, hour: int, text: str) -> dict:
    """Set the text for a single hourly slot in the user's day log.

    Merges into any existing day log for that date without disturbing the other
    hours. Creates the diary entry for the date if it does not exist yet.

    Args:
        date: The day to write, in ISO ``YYYY-MM-DD`` format. Required.
        hour: The hour slot to set, an integer from 0 to 23.
        text: What the user did during that hour. Pass an empty string to clear
            the slot.

    Returns:
        ``{"ok": True, "date": ..., "hour": ..., "day_log": {...}}`` with the
        updated log, or ``{"ok": False, "error": "..."}`` on invalid input.
    """
    clean_date = (date or "").strip()
    if not clean_date:
        return {"ok": False, "error": "date is required (YYYY-MM-DD)."}
    try:
        hour_int = int(hour)
    except (TypeError, ValueError):
        return {"ok": False, "error": "hour must be an integer from 0 to 23."}
    if not (0 <= hour_int <= 23):
        return {"ok": False, "error": "hour must be between 0 and 23."}

    user_id = require_user_id()
    client = get_supabase_service_client()
    existing = (
        client.table("diary")
        .select("day_log")
        .eq("user_id", user_id)
        .eq("date", clean_date)
        .limit(1)
        .execute()
    )
    rows = existing.data or []
    day_log = dict(rows[0].get("day_log") or {}) if rows else {}
    day_log[str(hour_int)] = text

    payload = {"user_id": user_id, "date": clean_date, "day_log": day_log}
    try:
        client.table("diary").upsert(payload, on_conflict="user_id,date").execute()
    except Exception as exc:  # noqa: BLE001 - surface a structured error to the model
        return {"ok": False, "error": f"Failed to update day log: {exc}"}

    return {"ok": True, "date": clean_date, "hour": hour_int, "day_log": day_log}
