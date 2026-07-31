"""
Query-building agent for the knowledge-bits pipeline.

This is the pipeline's query stage (see
``api.v1.kbits_api.pipeline.query.AgentQuery``). The agent reads the user's live
situation — goals, diary, calendar, tasks and the bits they have already been
shown — with read-only tools, then states what kind of bits they need now. The
generate stage takes it from there, so this agent never writes a bit itself.

It reports its answer by calling ``submit_kbit_query``, which makes the tool's
arguments the structured output. That sidesteps ADK's ``output_schema``, which is
enforced unreliably once an agent has tools of its own.

Runs are ephemeral: an in-memory session is created per run and deleted after,
because query building is a batch step with no history worth keeping (unlike
chat, which persists sessions to Postgres).
"""

import logging
import uuid
from functools import lru_cache

from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types

from tools.context import require_user_id
from tools.registry import KBIT_QUERY_TOOLS
from config.llm_keys import get_litellm_kwargs
from config.models import get_default_model_id

logger = logging.getLogger(__name__)

# Kept distinct from the chat agent's APP_NAME so these sessions can never
# collide with a user's persisted conversations.
APP_NAME = "f5-kbit-query"

# Bounds the tool loop. Query building should be a handful of reads, and
# ``POST /kbits/invoke`` waits on it, so runaway tool calling is a latency bug.
MAX_LLM_CALLS = 10

SUBMIT_TOOL_NAME = "submit_kbit_query"

INSTRUCTION = (
    "You decide what kind of knowledge bits a personal-growth app should "
    "generate for one user right now. You do not write the bits — another stage "
    "does that from the query you submit.\n\n"
    "First read the user's actual situation with your tools. Goals "
    "(list_my_goals, get_goal, list_child_goals, search_goals) tell you what they "
    "are working toward. Diary and day logs (get_recent_diary_entries, "
    "search_diary, get_diary_entry) tell you how their days are really going and "
    "where they are stuck. Recent bits (list_recent_kbits, get_knowledge_bit, "
    "search_kbits) tell you what they have already been shown, and how they "
    "reacted — liked, disliked and rated bits are your best signal for what lands "
    "with this person. Calendar and tasks (list_calendar_events, list_tasks) tell "
    "you what is coming up, which can make a bit timely. Prefer a few "
    "well-chosen calls over exhaustive reads. If a Google tool reports that the "
    "user is not connected, move on without it.\n\n"
    "Then call submit_kbit_query exactly once with:\n"
    "include — short topic phrases naming what to seek, one per distinct angle. "
    "These are matched against candidate bits when ranking, so keep them "
    "specific and keyword-like rather than full sentences.\n"
    "exclude — short phrases for ground already covered by their recent bits, or "
    "that they disliked.\n"
    "brief — a few sentences of prose on what this user needs right now and why, "
    "grounded in what you actually read. Name the specifics: which goal is "
    "stalling, what their days show, what is coming up.\n\n"
    "Never invent facts about the user. If the tools return little, say so in the "
    "brief and keep the query broad rather than fabricating detail — a thin query "
    "built on real data beats a rich invented one. Never call a tool that writes "
    "or changes data."
)


def submit_kbit_query(include: list[str], exclude: list[str], brief: str) -> dict:
    """Submit the finished query describing which knowledge bits to generate.

    Call this exactly once, after reading the user's situation. Its arguments are
    the result of your work; there is nothing to do afterwards.

    Args:
        include: Short topic phrases naming what the bits should cover, one per
            distinct angle.
        exclude: Short phrases for ground the user has already covered or
            disliked.
        brief: A few sentences on what this user needs right now and why,
            grounded in what the tools returned.

    Returns:
        ``{"ok": True}`` once the query has been recorded.
    """
    return {
        "ok": True,
        "include_count": len(include or []),
        "exclude_count": len(exclude or []),
    }


def build_kbit_query_agent(model_id: str | None = None) -> LlmAgent:
    """Create the query-building agent: read-only tools plus the submit tool."""
    resolved_model = model_id or get_default_model_id()
    return LlmAgent(
        model=LiteLlm(**get_litellm_kwargs(resolved_model)),
        name="kbit_query_builder",
        instruction=INSTRUCTION,
        tools=[*KBIT_QUERY_TOOLS, FunctionTool(submit_kbit_query)],
    )


@lru_cache
def get_query_session_service() -> InMemorySessionService:
    """Cached in-memory session service; query-building runs are never persisted."""
    return InMemorySessionService()


@lru_cache
def _get_query_runner(model_id: str) -> Runner:
    return Runner(
        agent=build_kbit_query_agent(model_id),
        app_name=APP_NAME,
        session_service=get_query_session_service(),
    )


def _as_str_list(value) -> list[str]:
    """Coerce a submitted term list, tolerating a bare string or stray types."""
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


async def build_kbit_query(
    count: int, goal_id: str | None = None, *, model_id: str | None = None
) -> dict | None:
    """Run the query agent and return its submitted query.

    Returns ``{"include", "exclude", "brief"}``, or ``None`` if the agent never
    called ``submit_kbit_query`` so the caller can fall back to a simpler query
    strategy. Plain dicts keep this module independent of the pipeline's types.

    The signed-in user comes from ``current_user_id`` (set by the pipeline
    orchestrator), which is also how the tools scope their reads.
    """
    user_id = require_user_id()
    runner = _get_query_runner(model_id or get_default_model_id())
    session_service = get_query_session_service()
    session_id = str(uuid.uuid4())

    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

    task = f"Build a query for {count} knowledge bits."
    if goal_id:
        task += (
            f" Focus only on the goal with id {goal_id}; read it with get_goal "
            "and ignore the user's other goals."
        )

    submitted: dict | None = None
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=task)]),
            run_config=RunConfig(max_llm_calls=MAX_LLM_CALLS),
        ):
            if not event.content or not event.content.parts:
                continue
            for part in event.content.parts:
                call = part.function_call
                if call and call.name == SUBMIT_TOOL_NAME:
                    submitted = dict(call.args or {})
    finally:
        await session_service.delete_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    if submitted is None:
        logger.warning(
            "Query agent finished without submitting a query",
            extra={"user_id": user_id},
        )
        return None

    query = {
        "include": _as_str_list(submitted.get("include")),
        "exclude": _as_str_list(submitted.get("exclude")),
        "brief": str(submitted.get("brief") or "").strip(),
    }
    logger.info(
        "Kbit query built by agent",
        extra={
            "user_id": user_id,
            "include_count": len(query["include"]),
            "exclude_count": len(query["exclude"]),
        },
    )
    return query
