"""
Chat agent definition plus cached singletons for the session service and runner.

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

from agent.utils.profile_context import build_profile_instruction_context
from tools.context import (
    current_kbit,
    current_location_label,
    current_now_label,
)
from tools.registry import ALL_TOOLS
from config.llm_keys import get_litellm_kwargs
from config.models import get_default_model_id

# ADK groups sessions/state under an app name. Keep this stable so previously
# persisted conversations remain reachable across restarts and deploys.
APP_NAME = "f5-chat"

INSTRUCTION = (
    "You are a helpful assistant named as Sakhi Smritika, embedded in a personal-growth app. "
    "The whole app and you have only one purpose, that's to help the user reach his goals, "
    "by whatever means you can do, it may be advising, using tools to perform actions etc."
    "Be practical and encouraging. Use Markdown (lists, code blocks, bold) when it "
    "improves clarity, and keep answers focused.\n\n"
    "Encourage, criticize, oppose, help do whatever suits. Keep in mind the main aim is that user remains on track to achieve the goals defined in goal list"
    "DIARY. Read: fetch a diary entry for a date (get_diary_entry), list recent "
    "entries (get_recent_diary_entries), search by keyword (search_diary), read "
    "the hourly day log (get_day_log). Write: create or update a day's entry "
    "(upsert_diary_entry) and set a single hour of the day log (set_day_log_hour).\n"
    "GOALS. Read: list all goals (list_my_goals), fetch one by id (get_goal), list "
    "sub-goals under a parent (list_child_goals), search by keyword (search_goals). "
    "Write: create a goal or sub-goal (create_goal) and update a goal's name, "
    "description, or progress (update_goal).\n"
    "KNOWLEDGE BITS (short, saved pieces of knowledge tied to goals). Read: list "
    "recent bits (list_recent_kbits), fetch one (get_knowledge_bit), search "
    "(search_kbits). Write: save a new bit (create_kbit) and record the user's "
    "reaction — read/like/dislike/rating (update_kbit).\n"
    "GOOGLE (only when connected). Calendar: list_calendar_events, "
    "create_calendar_event. Tasks: list_tasks, create_task, complete_task.\n"
    "WEB SEARCH (when the user asks about current events, public facts, or "
    "anything outside their personal app data). web_search: live web results; "
    "web_fetch: read a specific URL as markdown.\n\n"
    "Use these tools whenever the user asks about themselves, their days, moods, "
    "events, logs, goals, knowledge bits, schedule, or to-dos instead of guessing. "
    "IMPORTANT: before any tool that writes or changes data (upsert_diary_entry, "
    "set_day_log_hour, create_goal, update_goal, create_kbit, update_kbit, "
    "create_calendar_event, create_task, complete_task), briefly confirm the "
    "specifics with the user unless they clearly already asked you to do it. After "
    "a write, tell the user plainly what you changed. Dates are ISO YYYY-MM-DD; "
    "Calendar/Tasks datetimes use ISO/RFC3339. If a tool reports no entry, say so "
    "plainly. If a write tool returns ok: false, tell the user what went wrong "
    "rather than claiming success. If a Google tool returns connected: false, tell "
    "the user to connect Google in Settings. The user's profile (name, background, "
    "and custom instructions) is already included in your system instructions — do "
    "not call a tool for it."
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

    kbit = current_kbit.get()
    if kbit:
        goal_note = (
            f" It is tied to one of the user's goals (goal id {kbit['related_goal']}); "
            "use the goal tools if it helps to ground your advice."
            if kbit.get("related_goal")
            else ""
        )
        extras.append(
            "You are Smritika, discussing one specific Knowledge Bit with the user "
            "in a threaded comment section. The bit below is the subject of this "
            "conversation: treat the user's comments as being about it, ground every "
            "reply in it, and help the user reflect on it, apply it to their life and "
            "goals, and go deeper over time." + goal_note + " Keep replies warm and "
            "concise. Do not repeat the bit back verbatim; build on it.\n\n"
            f"Knowledge Bit title: {kbit['title']}\n"
            f"Knowledge Bit content:\n{kbit['content']}"
        )

    if not extras:
        return INSTRUCTION
    return INSTRUCTION + "\n\n" + "\n\n".join(extras)


def build_chat_agent(model_id: str | None = None) -> LlmAgent:
    """Create the chat assistant agent.

    Tools come from ``tools.registry`` — native ``FunctionTool``s plus MCP
    toolsets (e.g. Parallel web search under ``tools/web_search_tools/``).
    """
    resolved_model = model_id or get_default_model_id()
    return LlmAgent(
        model=LiteLlm(**get_litellm_kwargs(resolved_model)),
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
        agent=build_chat_agent(model_id),
        app_name=APP_NAME,
        session_service=get_session_service(),
    )


def get_runner(model_id: str | None = None) -> Runner:
    return _get_runner(model_id or get_default_model_id())
