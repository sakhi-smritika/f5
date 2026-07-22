"""Seed data for auth users and public.users profiles."""

SEED_USERS = [
    {
        "email": "seed_user@gmail.com",
        "password": "password123",
        "user_metadata": {"name": "Seed User"},
        "profile": {
            "username": "seed_user",
            "display_name": "Seed User",
            "full_name": "Seed User",
            "user_information": (
                "Primary seed account for local development. Uses the app for diary "
                "entries, day logs, and goal tracking."
            ),
            "system_instructions": (
                "Be concise and encouraging. Reference diary and goals when relevant."
            ),
        },
    },
    {
        "email": "test@example.com",
        "password": "password123",
        "user_metadata": {"name": "Test User"},
        "profile": {
            "username": "test_user",
            "display_name": "Test User",
            "full_name": "Test User",
            "user_information": (
                "Secondary test account for automated checks and manual QA."
            ),
            "system_instructions": "Keep answers short and focused on the question asked.",
        },
    },
]


def seed_user_emails() -> list[str]:
    return [user["email"] for user in SEED_USERS]
