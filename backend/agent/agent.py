"""
ADK agent definition plus cached singletons for the session service and runner.

The agent uses LiteLLM-backed models and persists every conversation
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

from agent.profile_context import build_profile_instruction_context
from agent.tools.context import current_location_label, current_now_label
from agent.tools.registry import ALL_TOOLS
from config.llm_keys import get_api_key_for_model
from config.models import get_default_model_id

# ADK groups sessions/state under an app name. Keep this stable so previously
# persisted conversations remain reachable across restarts and deploys.
APP_NAME = "f5-chat"

INSTRUCTION = (
    "You are a helpful, concise assistant embedded in a personal-growth web app. "
    "Be practical and encouraging. Use Markdown (lists, code blocks, bold) when it "
    "improves clarity, and keep answers focused.\n\n"
    "You can look up the signed-in user's own data with your tools: fetch a diary entry for a date (get_diary_entry), "
    "list recent entries (get_recent_diary_entries), search the diary by keyword "
    "(search_diary), and read the hourly day log (get_day_log). For goals, list "
    "all goals (list_my_goals), fetch one by id (get_goal), list sub-goals under "
    "a parent (list_child_goals), or search goals by keyword (search_goals). When Google is "
    "connected, you can also list or create Calendar events (list_calendar_events, "
    "create_calendar_event) and list, create, or complete Tasks (list_tasks, "
    "create_task, complete_task). Use these tools whenever the user asks about "
    "themselves, their days, moods, events, logs, goals, schedule, or to-dos instead of "
    "guessing. Dates are ISO YYYY-MM-DD; Calendar/Tasks datetimes use ISO/RFC3339. "
    "If a tool reports no entry, say so plainly. If a Google tool returns "
    "connected: false, tell the user to connect Google in Settings. The user's "
    "profile (name, background, and custom instructions) is already included in "
    "your system instructions — do not call a tool for it."
)


def _instruction_provider(_ctx) -> str:
    """Dynamic instruction: append profile, date/time, and location per request."""
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

    profile_context = build_profile_instruction_context()
    if profile_context:
        extras.append(profile_context)

    if not extras:
        return INSTRUCTION
    return INSTRUCTION + "\n\n" + "\n\n".join(extras)


def build_agent(model_id: str | None = None) -> LlmAgent:
    """Create the root agent.

    Tools are plain Python functions wrapped as ADK ``FunctionTool``s in
    ``agent.tools.registry``. To connect MCP servers later, add ``McpToolset(...)``
    entries alongside them:

        from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
        tools=[*ALL_TOOLS, McpToolset(connection_params=StreamableHTTPConnectionParams(url=..., headers=...))]
    """
    resolved_model = model_id or get_default_model_id()
    return LlmAgent(
        model=LiteLlm(
            model=resolved_model,
            api_key=get_api_key_for_model(resolved_model),
        ),
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
def _get_runner(model_id: str) -> Runner:
    """Cached ``Runner`` wiring the agent to the persistent session service."""
    return Runner(
        agent=build_agent(model_id),
        app_name=APP_NAME,
        session_service=get_session_service(),
    )


def get_runner(model_id: str | None = None) -> Runner:
    return _get_runner(model_id or get_default_model_id())
