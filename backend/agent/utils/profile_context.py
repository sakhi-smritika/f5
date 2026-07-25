"""
Profile context injected into the agent system prompt on every chat request.

This is not exposed as a tool — the assistant receives the signed-in user's
profile fields directly in its instructions.
"""

from config.supabase import get_supabase_service_client

from tools.context import current_user_id

_PROFILE_COLUMNS = "display_name, full_name, user_information, system_instructions"


def _fetch_profile_row(user_id: str) -> dict | None:
    result = (
        get_supabase_service_client()
        .table("users")
        .select(_PROFILE_COLUMNS)
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def build_profile_instruction_context() -> str:
    """Build a system-prompt suffix from the signed-in user's profile fields."""
    user_id = current_user_id.get()
    if not user_id:
        return ""

    profile = _fetch_profile_row(user_id)
    if profile is None:
        return ""

    parts: list[str] = []

    full_name = (profile.get("full_name") or "").strip()
    if full_name:
        parts.append(f"The user's full name is {full_name}.")

    display_name = (profile.get("display_name") or "").strip()
    if display_name and display_name != full_name:
        parts.append(f"The user's display name is {display_name}.")

    user_information = (profile.get("user_information") or "").strip()
    if user_information:
        parts.append(f"Background about the user:\n{user_information}")

    system_instructions = (profile.get("system_instructions") or "").strip()
    if system_instructions:
        parts.append(
            "The user has set these instructions for how you should behave:\n"
            f"{system_instructions}"
        )

    if not parts:
        return ""

    return (
        "The following profile context applies to the signed-in user. "
        "Follow it closely, especially any system instructions.\n\n"
        + "\n\n".join(parts)
    )
