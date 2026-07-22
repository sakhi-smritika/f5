"""
Seed script to create dummy users in Supabase auth.
Uses the Supabase Admin API to create users with email/password.
DO NOT CHANGE THE EMAIL OR PASSWORD of the seeded users, as they are used in other seed scripts and tests.
"""

import logging
from typing import Any

from .data.users import SEED_USERS
from .utils import get_admin_client, get_user_id_by_email, list_auth_users

logger = logging.getLogger(__name__)


def get_existing_user_emails(users: list[Any]) -> set[str]:
    """Return emails for the given auth user records."""
    return {
        getattr(user, "email", None)
        for user in users
        if getattr(user, "email", None)
    }


def upsert_public_user_profile(supabase, user_id: str, profile: dict[str, str]) -> None:
    """Write profile fields into public.users for the given auth user id."""
    row = {
        "id": user_id,
        "username": profile.get("username"),
        "display_name": profile.get("display_name"),
        "full_name": profile.get("full_name"),
        "user_information": profile.get("user_information"),
        "system_instructions": profile.get("system_instructions"),
    }
    supabase.table("users").upsert(row, on_conflict="id").execute()


def seed_users():
    """Seed dummy users into Supabase auth and public.users profiles."""
    supabase = get_admin_client()
    auth_users = list_auth_users(supabase)
    existing_emails = get_existing_user_emails(auth_users)

    logger.info("Seeding %s users...", len(SEED_USERS))

    for user_data in SEED_USERS:
        email = user_data["email"]
        profile = user_data.get("profile", {})
        user_id = get_user_id_by_email(supabase, email)

        if email in existing_emails and user_id:
            logger.info("User already exists: %s", email)
        else:
            try:
                response = supabase.auth.admin.create_user(
                    {
                        "email": email,
                        "password": user_data["password"],
                        "email_confirm": True,
                        "user_metadata": user_data.get("user_metadata", {}),
                    }
                )
                user_id = str(response.user.id)
                auth_users.append(response.user)
                existing_emails.add(email)
                logger.info("Created user: %s (ID: %s)", email, user_id)
            except Exception as exc:
                error_msg = str(exc)
                if "already been registered" in error_msg or "already exists" in error_msg:
                    logger.warning("User already exists: %s", email)
                    existing_emails.add(email)
                    user_id = get_user_id_by_email(supabase, email)
                else:
                    logger.error("Failed to create user %s: %s", email, error_msg)
                    continue

        if not user_id:
            logger.error("Could not resolve user id for %s; skipping profile seed.", email)
            continue

        try:
            upsert_public_user_profile(supabase, user_id, profile)
            logger.info(
                "Updated public.users profile for %s (display_name=%s)",
                email,
                profile.get("display_name"),
            )
        except Exception as exc:
            logger.error("Failed to seed profile for %s: %s", email, exc)

    logger.info("\nSeeding complete!")


if __name__ == "__main__":
    seed_users()
