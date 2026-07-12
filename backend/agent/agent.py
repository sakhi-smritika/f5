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

from agent.tools.context import current_location_label, current_now_label
from agent.tools.registry import ALL_TOOLS

# ADK groups sessions/state under an app name. Keep this stable so previously
# persisted conversations remain reachable across restarts and deploys.
APP_NAME = "f5-chat"

# LiteLLM model string. "openai/<model>" routes to OpenAI using OPENAI_API_KEY.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-4o")

INSTRUCTION = (
    "You are a helpful, concise assistant embedded in a personal-growth web app. "
    "Be practical and encouraging. Use Markdown (lists, code blocks, bold) when it "
    "improves clarity, and keep answers focused.\n\n"
    "You can look up the signed-in user's own data with your tools: read their "
    "profile (get_my_profile), fetch a diary entry for a date (get_diary_entry), "
    "list recent entries (get_recent_diary_entries), search the diary by keyword "
    "(search_diary), and read the hourly day log (get_day_log). When Google is "
    "connected, you can also list or create Calendar events (list_calendar_events, "
    "create_calendar_event) and list, create, or complete Tasks (list_tasks, "
    "create_task, complete_task). Use these tools whenever the user asks about "
    "themselves, their days, moods, events, logs, schedule, or to-dos instead of "
    "guessing. Dates are ISO YYYY-MM-DD; Calendar/Tasks datetimes use ISO/RFC3339. "
    "If a tool reports no entry, say so plainly. If a Google tool returns "
    "connected: false, tell the user to connect Google in Settings."
)


def _instruction_provider(_ctx) -> str:
    """Dynamic instruction: append the user's current local date/time and location.

    These labels are set per request from the client, so the model can correctly
    resolve relative dates like "today"/"yesterday" (instead of assuming its
    training-time date) and reason about where the user is.
    """
    extras: list[str] = []

    now_label = current_now_label.get()
    if now_label:
        extras.append(
            f"The user's current local date and time is {now_label}. Always use "
            "this as the reference point when resolving relative dates such as "
            "'today', 'yesterday', 'this week' or 'last month'."
        )

    location_label = current_location_label.get()
    if location_label:
        extras.append(
            f"The user's approximate location is {location_label}. Use it only "
            "when location is relevant, and don't assume more precision than given."
        )

    if not extras:
        return INSTRUCTION
    return INSTRUCTION + "\n\n" + "\n\n".join(extras)


def build_agent() -> LlmAgent:
    """Create the root agent.

    Tools are plain Python functions wrapped as ADK ``FunctionTool``s in
    ``agent.tools.registry``. To connect MCP servers later, add ``McpToolset(...)``
    entries alongside them:

        from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
        tools=[*ALL_TOOLS, McpToolset(connection_params=StreamableHTTPConnectionParams(url=..., headers=...))]
    """
    return LlmAgent(
        model=LiteLlm(model=OPENAI_MODEL),
        name="assistant",
        instruction=_instruction_provider,
        tools=list(ALL_TOOLS),
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
