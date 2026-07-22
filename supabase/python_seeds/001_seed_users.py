"""
Seed script to create dummy users in Supabase auth.
Uses the Supabase Admin API to create users with email/password.
DO NOT CHANGE THE EMAIL OR PASSWORD of the seeded users, as they are used in other seed scripts and tests.
"""

import logging
from .utils import get_admin_client

logger = logging.getLogger(__name__)

# Dummy users to seed
SEED_USERS = [
    {
        "email": "seed_user@gmail.com",
        "password": "password123",
        "user_metadata": {"name": "Seed User"},
    },
    {
        "email": "test@example.com",
        "password": "password123",
        "user_metadata": {"name": "Test User"},
    },
]


def get_existing_user_emails(supabase) -> set[str]:
    """Return all existing user emails from Supabase auth."""
    try:
        response = supabase.auth.admin.list_users()
        users = getattr(response, "users", None) or []
        logger.info(f"Found {len(users)} existing users in Supabase auth.")
        logger.debug(f"Existing users: {[getattr(user, 'email', None) for user in users]}")
        return {
            getattr(user, "email", None)
            for user in users
            if getattr(user, "email", None)
        }
    except Exception as exc:
        logger.error(f"⚠ Could not list existing users: {exc}")
        return set()


def seed_users():
    """Seed dummy users into Supabase auth."""
    supabase = get_admin_client()
    existing_emails = get_existing_user_emails(supabase)

    logger.info(f"Seeding {len(SEED_USERS)} users...")

    for user_data in SEED_USERS:
        email = user_data["email"]
        if email in existing_emails:
            logger.info(f"↺ User already exists: {email}")
            continue

        try:
            # Use admin API to create user (bypasses email confirmation)
            response = supabase.auth.admin.create_user(
                {
                    "email": email,
                    "password": user_data["password"],
                    "email_confirm": True,  # Auto-confirm email
                    "user_metadata": user_data.get("user_metadata", {}),
                }
            )
            logger.info(f"✓ Created user: {email} (ID: {response.user.id})")
            existing_emails.add(email)
        except Exception as e:
            error_msg = str(e)
            if "already been registered" in error_msg or "already exists" in error_msg:
                logger.warning(f"⚠ User already exists: {email}")
                existing_emails.add(email)
            else:
                logger.error(f"✗ Failed to create user {email}: {error_msg}")

    logger.info("\nSeeding complete!")


if __name__ == "__main__":
    seed_users()
