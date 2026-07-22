#!/usr/bin/env python3
"""
Seed sample chat conversations using the ADK agent runner.

This script mirrors the backend's approach:
- create a conversation metadata row in public.conversations
- create an ADK session for the same conversation id
- use the LlmAgent + Runner to execute the assistant, which automatically
  persists both user and assistant messages to the session

The ADK session service will create the required database tables automatically
when they do not already exist, so no separate migration is required for this.
"""

import asyncio
import logging
import os
import sys
import uuid
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types as genai_types

from .utils import get_admin_client

logger = logging.getLogger(__name__)

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

DEFAULT_USER_EMAILS = [user_data["email"] for user_data in SEED_USERS]

SAMPLE_CONVERSATIONS = [
    {
        "title": "Morning reflection",
        "user_text": "Help me reflect on my day and pick one thing to improve tomorrow.",
    },
    {
        "title": "Weekly goals",
        "user_text": "I want to build a better weekly plan for my goals.",
    },
]

APP_NAME = "f5-chat"
DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_INSTRUCTION = (
    "You are a helpful, concise assistant embedded in a personal-growth web app. "
    "Be practical and encouraging. Use Markdown (lists, code blocks, bold) when it "
    "improves clarity, and keep answers focused."
)


def get_openai_api_key() -> str:
    """Get the OpenAI API key from environment."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in environment")
    return api_key



def get_session_service() -> DatabaseSessionService:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required to run the ADK session seed flow."
        )
    return DatabaseSessionService(db_url=database_url)


def build_agent() -> LlmAgent:
    """Build the LlmAgent for seeding using OpenAI."""
    return LlmAgent(
        model=LiteLlm(
            model=DEFAULT_MODEL,
            api_key=get_openai_api_key(),
        ),
        name="assistant",
        instruction=SYSTEM_INSTRUCTION,
        tools=[],  # No tools for seeding
    )


def get_runner() -> Runner:
    """Get a Runner that wires the agent to the session service."""
    return Runner(
        agent=build_agent(),
        app_name=APP_NAME,
        session_service=get_session_service(),
    )


async def prepare_session_tables(session_service: DatabaseSessionService) -> None:
    await session_service.prepare_tables()


def resolve_user_ids(admin_client: Any) -> list[str]:
    """Resolve seed user IDs from Supabase auth."""
    response = admin_client.auth.admin.list_users()
    users = response if isinstance(response, list) else getattr(response, "users", None) or []
    logger.info(f"Found {len(users)} users in Supabase auth for seeding conversations")
    matched_ids: list[str] = []
    for user in users:
        email = getattr(user, "email", None)
        if email in DEFAULT_USER_EMAILS:
            logger.info(f"Found user {email} with ID {user.id} for seeding conversations")
            matched_ids.append(str(user.id))
        else:
            logger.debug(f"Skipping user {email} with ID {user.id} for seeding conversations")

    if matched_ids:
        return matched_ids

    raise RuntimeError("No Supabase users were found to attach seeded conversations to.")


def create_conversation(client: Any, *, user_id: str, title: str) -> str:
    """Create a conversation metadata row in Supabase."""
    try:
        conversation_id = str(uuid.uuid4())
        client.table("conversations").insert(
            {"id": conversation_id, "user_id": user_id, "title": title}
        ).execute()
        logger.info(
            f"✓ Created conversation {conversation_id} for user {user_id} with title '{title}'"
        )
        return conversation_id
    except Exception as exc:
        logger.error(f"⚠ Could not create conversation for user {user_id}: {exc}")
        raise


def conversation_exists(client: Any, *, user_id: str, title: str) -> bool:
    """Check if a conversation with the given title already exists for the user."""
    try:
        response = (
            client.table("conversations")
            .select("id")
            .eq("user_id", user_id)
            .eq("title", title)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return bool(rows)
    except Exception as exc:
        logger.error(
            f"⚠ Could not check if conversation exists for user {user_id}: {exc}"
        )
        raise


async def seed_conversation_with_agent(
    runner: Runner,
    client: Any,
    *,
    user_id: str,
    sample: dict[str, str],
) -> None:
    """
    Create a conversation and seed it with a user message and an LLM-generated response.

    This uses the Runner (LlmAgent + DatabaseSessionService) to properly execute
    the agent, which automatically persists both user and assistant messages.
    """
    title = sample["title"]
    user_text = sample["user_text"]

    if conversation_exists(client, user_id=user_id, title=title):
        print(f"↺ Conversation already exists for user {user_id}: {title}")
        return

    conversation_id = create_conversation(client, user_id=user_id, title=title)

    # Create the ADK session for this conversation
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=conversation_id
    )

    # Execute the agent via runner.run_async(), which persists both messages automatically
    try:
        new_message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_text)],
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=conversation_id,
            new_message=new_message,
            run_config=RunConfig(),
        ):
            # Events are automatically persisted by the runner.
            # We just consume them here to ensure the full run completes.
            pass

        print(
            f"✓ Seeded conversation {conversation_id} for user {user_id} with title '{title}'"
        )
    except Exception as exc:
        logger.exception(
            f"Failed to seed conversation {conversation_id}",
            extra={"user_id": user_id, "title": title},
        )
        raise


async def seed_conversations() -> None:
    """Main seeding function: create conversations and seed them with agent responses."""
    try:
        admin_client = get_admin_client()
        service_client = get_admin_client()
        session_service = get_session_service()

        await prepare_session_tables(session_service)

        # Get or create the runner (wires agent to session service)
        runner = get_runner()

        user_ids = resolve_user_ids(admin_client)
        print(f"Found {len(user_ids)} user(s) for seeding conversations")

        for user_id in user_ids:
            for sample in SAMPLE_CONVERSATIONS:
                await seed_conversation_with_agent(
                    runner,
                    service_client,
                    user_id=user_id,
                    sample=sample,
                )

        print("✓ Conversation seeding complete")
    except Exception as exc:
        logger.exception("Conversation seeding failed")
        sys.exit(1)


def main() -> None:
    asyncio.run(seed_conversations())


if __name__ == "__main__":
    main()
