"""
ADK agent definition plus cached singletons for the session service and runner.

The agent uses an OpenAI model through LiteLLM and persists every conversation
(session + events) in the Supabase Postgres database via ADK's
``DatabaseSessionService``. Per-user isolation is enforced by keying every ADK
session with the authenticated Supabase user id.
"""

import os
from functools import lru_cache

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

# ADK groups sessions/state under an app name. Keep this stable so previously
# persisted conversations remain reachable across restarts and deploys.
APP_NAME = "f5-chat"

# LiteLLM model string. "openai/<model>" routes to OpenAI using OPENAI_API_KEY.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-4o")

INSTRUCTION = (
    "You are a helpful, concise assistant embedded in a personal-growth web app. "
    "Be practical and encouraging. Use Markdown (lists, code blocks, bold) when it "
    "improves clarity, and keep answers focused."
)


def build_agent() -> LlmAgent:
    """Create the root agent.

    To connect MCP servers later, add ``McpToolset(...)`` entries to ``tools``:

        from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
        tools=[McpToolset(connection_params=StreamableHTTPConnectionParams(url=..., headers=...))]
    """
    return LlmAgent(
        model=LiteLlm(model=OPENAI_MODEL),
        name="assistant",
        instruction=INSTRUCTION,
        tools=[],
    )


@lru_cache
def get_session_service() -> DatabaseSessionService:
    """Cached ``DatabaseSessionService`` bound to the Supabase Postgres database.

    ``DATABASE_URL`` must be an async SQLAlchemy URL, e.g.
    ``postgresql+asyncpg://postgres:<password>@<host>:5432/postgres``.
    """
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required for chat persistence "
            "(expected postgresql+asyncpg://... pointing at your Supabase database)"
        )
    return DatabaseSessionService(db_url=db_url)


@lru_cache
def get_runner() -> Runner:
    """Cached ``Runner`` wiring the agent to the persistent session service."""
    return Runner(
        agent=build_agent(),
        app_name=APP_NAME,
        session_service=get_session_service(),
    )
