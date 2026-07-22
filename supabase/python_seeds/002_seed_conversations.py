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

from .data.conversations import (
    APP_NAME,
    DEFAULT_MODEL,
    SAMPLE_CONVERSATIONS,
    SYSTEM_INSTRUCTION,
)
from .data.users import seed_user_emails
from .utils import get_admin_client, resolve_user_ids_by_emails

logger = logging.getLogger(__name__)


def get_openai_api_key() -> str:
    """Get the OpenAI API key from environment."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in environment")
    return api_key


def get_session_service() -> DatabaseSessionService:
    database_url = os.getenv("DATABASE_URL", "").strip()
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
        tools=[],
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
    user_ids_by_email = resolve_user_ids_by_emails(admin_client, seed_user_emails())
    logger.info(
        "Found %s seed user(s) in Supabase auth for conversation seeding",
        len(user_ids_by_email),
    )
    for email, user_id in user_ids_by_email.items():
        logger.info("Resolved %s -> %s", email, user_id)

    if user_ids_by_email:
        return list(user_ids_by_email.values())

    raise RuntimeError("No Supabase users were found to attach seeded conversations to.")


def create_conversation(client: Any, *, user_id: str, title: str) -> str:
    """Create a conversation metadata row in Supabase."""
    conversation_id = str(uuid.uuid4())
    client.table("conversations").insert(
        {"id": conversation_id, "user_id": user_id, "title": title}
    ).execute()
    logger.info(
        "Created conversation %s for user %s with title '%s'",
        conversation_id,
        user_id,
        title,
    )
    return conversation_id


def conversation_exists(client: Any, *, user_id: str, title: str) -> bool:
    """Check if a conversation with the given title already exists for the user."""
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


async def seed_conversation_with_agent(
    runner: Runner,
    client: Any,
    *,
    user_id: str,
    sample: dict[str, str],
) -> None:
    """Create a conversation and seed it with a user message and LLM response."""
    title = sample["title"]
    user_text = sample["user_text"]

    if conversation_exists(client, user_id=user_id, title=title):
        print(f"↺ Conversation already exists for user {user_id}: {title}")
        return

    conversation_id = create_conversation(client, user_id=user_id, title=title)

    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=conversation_id
    )

    new_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_text)],
    )
    async for _event in runner.run_async(
        user_id=user_id,
        session_id=conversation_id,
        new_message=new_message,
        run_config=RunConfig(),
    ):
        pass

    print(
        f"✓ Seeded conversation {conversation_id} for user {user_id} with title '{title}'"
    )


async def seed_conversations() -> None:
    """Create conversations and seed them with agent responses."""
    admin_client = get_admin_client()
    session_service = get_session_service()

    await prepare_session_tables(session_service)
    runner = get_runner()
    user_ids = resolve_user_ids(admin_client)

    print(f"Found {len(user_ids)} user(s) for seeding conversations")

    for user_id in user_ids:
        for sample in SAMPLE_CONVERSATIONS:
            await seed_conversation_with_agent(
                runner,
                admin_client,
                user_id=user_id,
                sample=sample,
            )

    print("✓ Conversation seeding complete")


def main() -> None:
    try:
        asyncio.run(seed_conversations())
    except Exception:
        logger.exception("Conversation seeding failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
