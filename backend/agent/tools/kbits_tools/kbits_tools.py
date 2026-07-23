"""
Tools over the user's Knowledge Bits (``public.knowledge_bits``).

Knowledge Bits are short, AI-curated pieces of knowledge tied to the user's
goals. These tools let the assistant read the user's feed, search it, create a
new bit, and record the user's reactions (read / like / dislike / rating).

Every function is scoped to the signed-in user via ``require_user_id()`` and
goes through the service-role Supabase client. Functions return plain,
JSON-serializable dicts so ADK can hand the result back to the model.
"""

from config.supabase import get_supabase_service_client

from ..context import require_user_id

# Columns exposed to the assistant. ``user_id`` is intentionally omitted.
_KBIT_COLUMNS = (
    "id, created_at, updated_at, title, content, related_goal, is_read, "
    "is_liked, is_disliked, rating"
)

# Bounds for the optional star rating (mirrors the kbits API).
_MIN_RATING = 1
_MAX_RATING = 5


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


def list_recent_kbits(limit: int = 10, unread_only: bool = False) -> dict:
    """List the user's most recent knowledge bits, newest first.

    Args:
        limit: Maximum number of bits to return (1-50). Defaults to 10.
        unread_only: When True, only return bits the user has not read yet.

    Returns:
        A dict with ``count`` and a list of ``bits`` ordered by creation date
        descending.
    """
    safe_limit = max(1, min(int(limit), 50))
    user_id = require_user_id()
    query = (
        get_supabase_service_client()
        .table("knowledge_bits")
        .select(_KBIT_COLUMNS)
        .eq("user_id", user_id)
    )
    if unread_only:
        query = query.eq("is_read", False)
    result = query.order("created_at", desc=True).limit(safe_limit).execute()
    bits = result.data or []
    return {"count": len(bits), "bits": bits}


def get_knowledge_bit(kbit_id: str) -> dict:
    """Get a single knowledge bit by id.

    Args:
        kbit_id: The bit's UUID.

    Returns:
        The bit's title, content, related goal, reaction flags and timestamps,
        or ``found`` ``False`` if it does not exist or belongs to another user.
    """
    kbit_id = (kbit_id or "").strip()
    if not kbit_id:
        return {"found": False, "note": "Empty kbit_id."}

    user_id = require_user_id()
    result = (
        get_supabase_service_client()
        .table("knowledge_bits")
        .select(_KBIT_COLUMNS)
        .eq("user_id", user_id)
        .eq("id", kbit_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return {"found": False, "kbit_id": kbit_id}
    return {"found": True, "bit": rows[0]}


def search_kbits(keyword: str) -> dict:
    """Search the user's knowledge bits for a keyword.

    Matches (case-insensitive) against the bit title and content.

    Args:
        keyword: The text to search for.

    Returns:
        A dict with ``count`` and matching ``bits`` (newest first).
    """
    term = (keyword or "").strip()
    if not term:
        return {"count": 0, "bits": [], "note": "Empty keyword."}

    user_id = require_user_id()
    # Inside a PostgREST `or` filter, ilike uses `*` (not `%`) as the wildcard,
    # and commas separate conditions, so strip commas from the term.
    pattern = "*" + term.replace(",", " ") + "*"
    or_filter = f"title.ilike.{pattern},content.ilike.{pattern}"
    result = (
        get_supabase_service_client()
        .table("knowledge_bits")
        .select(_KBIT_COLUMNS)
        .eq("user_id", user_id)
        .or_(or_filter)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    bits = result.data or []
    return {"count": len(bits), "bits": bits}


def create_kbit(title: str, content: str, related_goal_id: str = "") -> dict:
    """Create a new knowledge bit for the user.

    Use this to save a useful insight, tip or piece of knowledge to the user's
    feed. Optionally link it to one of the user's goals.

    Args:
        title: A short title for the bit. Required.
        content: The body of the bit (a concise, useful piece of knowledge).
            Required.
        related_goal_id: Optional UUID of a goal to link this bit to. Must be one
            of the user's own goals; leave empty for a general bit.

    Returns:
        ``{"ok": True, "bit": {...}}`` with the created bit, or
        ``{"ok": False, "error": "..."}`` on validation failure.
    """
    clean_title = (title or "").strip()
    clean_content = (content or "").strip()
    if not clean_title or not clean_content:
        return {"ok": False, "error": "Both title and content are required."}

    user_id = require_user_id()
    payload: dict = {
        "user_id": user_id,
        "title": clean_title,
        "content": clean_content,
    }

    goal_id = (related_goal_id or "").strip()
    if goal_id:
        if not _user_owns_goal(goal_id, user_id):
            return {
                "ok": False,
                "error": "related_goal_id does not match one of your goals.",
            }
        payload["related_goal"] = goal_id

    try:
        result = (
            get_supabase_service_client()
            .table("knowledge_bits")
            .insert(payload)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 - surface a structured error to the model
        return {"ok": False, "error": f"Failed to create bit: {exc}"}

    rows = result.data or []
    return {"ok": True, "bit": rows[0] if rows else None}


def update_kbit(
    kbit_id: str,
    is_read: bool | None = None,
    is_liked: bool | None = None,
    is_disliked: bool | None = None,
    rating: int | None = None,
) -> dict:
    """Record the user's reaction to a knowledge bit.

    Only the fields you pass are changed; omit the rest. Liking and disliking are
    mutually exclusive — setting one clears the other.

    Args:
        kbit_id: The bit's UUID.
        is_read: Mark the bit as read (True) or unread (False).
        is_liked: Like (True) or remove a like (False).
        is_disliked: Dislike (True) or remove a dislike (False).
        rating: A star rating from 1 to 5.

    Returns:
        ``{"ok": True, "updated": {...}}`` with the fields that changed, or
        ``{"ok": False, "error": "..."}`` if nothing valid was provided or the
        bit was not found.
    """
    kbit_id = (kbit_id or "").strip()
    if not kbit_id:
        return {"ok": False, "error": "Empty kbit_id."}

    updates: dict = {}
    if is_read is not None:
        updates["is_read"] = bool(is_read)
    if is_liked is not None:
        updates["is_liked"] = bool(is_liked)
        if is_liked:
            updates["is_disliked"] = False
    if is_disliked is not None:
        updates["is_disliked"] = bool(is_disliked)
        if is_disliked:
            updates["is_liked"] = False
    if rating is not None:
        if not (_MIN_RATING <= int(rating) <= _MAX_RATING):
            return {
                "ok": False,
                "error": f"rating must be between {_MIN_RATING} and {_MAX_RATING}.",
            }
        updates["rating"] = int(rating)

    if not updates:
        return {"ok": False, "error": "No fields to update."}

    user_id = require_user_id()
    result = (
        get_supabase_service_client()
        .table("knowledge_bits")
        .update(updates)
        .eq("id", kbit_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not (result.data or []):
        return {"ok": False, "error": "Knowledge bit not found."}
    return {"ok": True, "updated": {"id": kbit_id, **updates}}
