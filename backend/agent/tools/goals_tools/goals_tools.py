"""
Tools over the user's goals (``public.goals``).

Every function is scoped to the signed-in user via ``require_user_id()`` and
goes through the service-role Supabase client. Functions return plain,
JSON-serializable dicts so ADK can hand the result back to the model.
"""

from config.supabase import get_supabase_service_client

from ..context import require_user_id


def _user_owns_goal(goal_id: str, user_id: str) -> bool:
    """Return True if ``goal_id`` exists and belongs to ``user_id``."""
    result = (
        get_supabase_service_client()
        .table("goals")
        .select("id")
        .eq("user_id", user_id)
        .eq("id", goal_id)
        .limit(1)
        .execute()
    )
    return bool(result.data)

# Columns exposed to the assistant. ``user_id`` is intentionally omitted.
_GOAL_COLUMNS = (
    "id, goal_name, goal_description, progress, parent_goal, created_at, updated_at"
)


def list_my_goals(limit: int = 50) -> dict:
    """List the signed-in user's goals in a flat list, newest first.

    Root goals have ``parent_goal`` set to ``null``; sub-goals reference their
    parent's ``id``. Use ``list_child_goals`` to fetch only the children of a
    specific goal.

    Args:
        limit: Maximum number of goals to return (1-100). Defaults to 50.

    Returns:
        A dict with ``count`` and a list of ``goals``.
    """
    safe_limit = max(1, min(int(limit), 100))
    user_id = require_user_id()
    result = (
        get_supabase_service_client()
        .table("goals")
        .select(_GOAL_COLUMNS)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(safe_limit)
        .execute()
    )
    goals = result.data or []
    return {"count": len(goals), "goals": goals}


def get_goal(goal_id: str) -> dict:
    """Get a single goal by id.

    Args:
        goal_id: The goal's UUID.

    Returns:
        The goal's name, description, progress, parent reference and timestamps,
        or ``found`` ``False`` if it does not exist or belongs to another user.
    """
    goal_id = (goal_id or "").strip()
    if not goal_id:
        return {"found": False, "note": "Empty goal_id."}

    user_id = require_user_id()
    result = (
        get_supabase_service_client()
        .table("goals")
        .select(_GOAL_COLUMNS)
        .eq("user_id", user_id)
        .eq("id", goal_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return {"found": False, "goal_id": goal_id}
    return {"found": True, "goal": rows[0]}


def list_child_goals(parent_goal_id: str) -> dict:
    """List direct child goals under a parent goal.

    Args:
        parent_goal_id: The parent goal's UUID.

    Returns:
        A dict with ``count`` and a list of child ``goals``. Returns an empty
        list when the parent has no children or does not exist.
    """
    parent_goal_id = (parent_goal_id or "").strip()
    if not parent_goal_id:
        return {"count": 0, "goals": [], "note": "Empty parent_goal_id."}

    user_id = require_user_id()
    result = (
        get_supabase_service_client()
        .table("goals")
        .select(_GOAL_COLUMNS)
        .eq("user_id", user_id)
        .eq("parent_goal", parent_goal_id)
        .order("created_at", desc=True)
        .execute()
    )
    goals = result.data or []
    return {"count": len(goals), "goals": goals, "parent_goal_id": parent_goal_id}


def search_goals(keyword: str) -> dict:
    """Search the user's goals for a keyword.

    Matches (case-insensitive) against the goal name, description and progress
    text.

    Args:
        keyword: The text to search for.

    Returns:
        A dict with ``count`` and matching ``goals`` (newest first).
    """
    term = (keyword or "").strip()
    if not term:
        return {"count": 0, "goals": [], "note": "Empty keyword."}

    user_id = require_user_id()
    # Inside a PostgREST `or` filter, ilike uses `*` (not `%`) as the wildcard,
    # and commas separate conditions, so strip commas from the term.
    pattern = "*" + term.replace(",", " ") + "*"
    or_filter = (
        f"goal_name.ilike.{pattern},"
        f"goal_description.ilike.{pattern},"
        f"progress.ilike.{pattern}"
    )
    result = (
        get_supabase_service_client()
        .table("goals")
        .select(_GOAL_COLUMNS)
        .eq("user_id", user_id)
        .or_(or_filter)
        .order("created_at", desc=True)
        .limit(30)
        .execute()
    )
    goals = result.data or []
    return {"count": len(goals), "goals": goals}


def create_goal(
    goal_name: str,
    goal_description: str = "",
    progress: str = "",
    parent_goal_id: str = "",
) -> dict:
    """Create a new goal (or sub-goal) for the user.

    Confirm the goal's intent with the user before creating it.

    Args:
        goal_name: A short name for the goal. Required.
        goal_description: An optional longer description of the goal.
        progress: An optional free-text note on current progress.
        parent_goal_id: Optional UUID of an existing goal to nest this under as a
            sub-goal. Must be one of the user's own goals; leave empty for a
            top-level goal.

    Returns:
        ``{"ok": True, "goal": {...}}`` with the created goal, or
        ``{"ok": False, "error": "..."}`` on validation failure.
    """
    clean_name = (goal_name or "").strip()
    if not clean_name:
        return {"ok": False, "error": "goal_name is required."}

    user_id = require_user_id()
    payload: dict = {"user_id": user_id, "goal_name": clean_name}
    if goal_description:
        payload["goal_description"] = goal_description
    if progress:
        payload["progress"] = progress

    parent_id = (parent_goal_id or "").strip()
    if parent_id:
        if not _user_owns_goal(parent_id, user_id):
            return {
                "ok": False,
                "error": "parent_goal_id does not match one of your goals.",
            }
        payload["parent_goal"] = parent_id

    try:
        result = (
            get_supabase_service_client().table("goals").insert(payload).execute()
        )
    except Exception as exc:  # noqa: BLE001 - surface a structured error to the model
        return {"ok": False, "error": f"Failed to create goal: {exc}"}

    rows = result.data or []
    return {"ok": True, "goal": rows[0] if rows else None}


def update_goal(
    goal_id: str,
    goal_name: str | None = None,
    goal_description: str | None = None,
    progress: str | None = None,
) -> dict:
    """Update an existing goal's name, description, or progress note.

    Only the fields you pass are changed; omit the rest. Commonly used to record
    progress on a goal (e.g. after the user reports what they did).

    Args:
        goal_id: The goal's UUID. Required.
        goal_name: A new name for the goal.
        goal_description: A new description for the goal.
        progress: An updated free-text progress note.

    Returns:
        ``{"ok": True, "updated": {...}}`` with the fields that changed, or
        ``{"ok": False, "error": "..."}`` if nothing was provided or the goal was
        not found.
    """
    goal_id = (goal_id or "").strip()
    if not goal_id:
        return {"ok": False, "error": "goal_id is required."}

    updates: dict = {}
    if goal_name is not None:
        clean_name = goal_name.strip()
        if not clean_name:
            return {"ok": False, "error": "goal_name cannot be blank."}
        updates["goal_name"] = clean_name
    if goal_description is not None:
        updates["goal_description"] = goal_description
    if progress is not None:
        updates["progress"] = progress

    if not updates:
        return {"ok": False, "error": "No fields to update."}

    user_id = require_user_id()
    result = (
        get_supabase_service_client()
        .table("goals")
        .update(updates)
        .eq("id", goal_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not (result.data or []):
        return {"ok": False, "error": "Goal not found."}
    return {"ok": True, "updated": {"id": goal_id, **updates}}
