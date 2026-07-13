"""
Read-only tools over the user's goals (``public.goals``).

Every function is scoped to the signed-in user via ``require_user_id()`` and
reads through the service-role Supabase client. Functions return plain,
JSON-serializable dicts so ADK can hand the result back to the model.
"""

from config.supabase import get_supabase_service_client

from .context import require_user_id

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
