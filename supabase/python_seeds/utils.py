import os
from functools import lru_cache
from typing import Any

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")


@lru_cache(maxsize=1)
def get_admin_client() -> Any:
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SECRET_KEY must be set before running this seed script."
        )
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


def list_auth_users(supabase: Any) -> list[Any]:
    """Return all auth users from Supabase."""
    response = supabase.auth.admin.list_users()
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return response.get("users") or []
    users = getattr(response, "users", None)
    return list(users) if users else []


def _user_field(user: Any, field: str) -> Any:
    if isinstance(user, dict):
        return user.get(field)
    return getattr(user, field, None)


def get_user_id_by_email(supabase: Any, email: str) -> str | None:
    """Look up an auth user's id by email."""
    for user in list_auth_users(supabase):
        if _user_field(user, "email") == email:
            user_id = _user_field(user, "id")
            return str(user_id) if user_id else None
    return None


def resolve_user_ids_by_emails(supabase: Any, emails: list[str]) -> dict[str, str]:
    """Map seed user emails to auth user ids."""
    email_set = set(emails)
    resolved: dict[str, str] = {}
    for user in list_auth_users(supabase):
        user_email = _user_field(user, "email")
        user_id = _user_field(user, "id")
        if user_email in email_set and user_id:
            resolved[user_email] = str(user_id)
    return resolved
