"""
Read-only tools over the user's profile (``public.users``).
"""

from config.supabase import get_supabase_service_client

from .context import require_user_id


def get_my_profile() -> dict:
    """Get the signed-in user's profile.

    Returns:
        A dict with ``username`` and ``display_name`` for the current user, or
        ``found`` ``False`` if no profile row exists yet.
    """
    user_id = require_user_id()
    result = (
        get_supabase_service_client()
        .table("users")
        .select("username, display_name, created_at")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return {"found": False}
    return {"found": True, "profile": rows[0]}
