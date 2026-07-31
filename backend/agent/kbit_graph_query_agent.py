"""
Graph-scoped query agent for the knowledge-bits pipeline.

Reads one knowledge graph with read-only tools, picks an expansion node, and
submits a structured query for the generator stage.
"""

from __future__ import annotations

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

from config.llm_keys import get_litellm_kwargs
from config.models import get_default_model_id
from tools.context import require_user_id
from tools.registry import KBIT_GRAPH_QUERY_TOOLS

logger = logging.getLogger(__name__)

APP_NAME = "f5-kbit-graph-query"
MAX_LLM_CALLS = 10
SUBMIT_TOOL_NAME = "submit_kbit_query"

INSTRUCTION = (
    "You decide what knowledge bits to generate by expanding one concept in a "
    "user's knowledge graph. You do not write the bits — another stage does.\n\n"
    "Read the graph with your tools: nodes, neighbors, and bits already linked "
    "to nodes. Pick ONE concept node to expand — prefer frontier concepts with "
    "room to grow and concepts the user has shown interest in.\n\n"
    "Call submit_kbit_query exactly once with:\n"
    "include — short topic phrases for the expansion (node label + adjacent ideas).\n"
    "exclude — concepts and topics already covered by linked bits.\n"
    "brief — why this node is the right expansion point now.\n"
    "expansion_node_id — UUID of the node you chose to expand through.\n\n"
    "Never invent graph structure. Use only what the tools return."
)


def submit_kbit_query(
    include: list[str],
    exclude: list[str],
    brief: str,
    expansion_node_id: str,
) -> dict:
    """Submit the finished graph expansion query.

    Args:
        include: Short topic phrases naming what the bits should cover.
        exclude: Short phrases for ground already covered.
        brief: Why this expansion node was chosen.
        expansion_node_id: UUID of the concept node to expand through.

    Returns:
        ``{"ok": True}`` once recorded.
    """
    return {
        "ok": True,
        "expansion_node_id": expansion_node_id,
        "include_count": len(include or []),
    }


def build_kbit_graph_query_agent(model_id: str | None = None) -> LlmAgent:
    resolved_model = model_id or get_default_model_id()
    return LlmAgent(
        model=LiteLlm(**get_litellm_kwargs(resolved_model)),
        name="kbit_graph_query_builder",
        instruction=INSTRUCTION,
        tools=[*KBIT_GRAPH_QUERY_TOOLS, FunctionTool(submit_kbit_query)],
    )


@lru_cache
def get_graph_query_session_service() -> InMemorySessionService:
    return InMemorySessionService()


@lru_cache
def _get_graph_query_runner(model_id: str) -> Runner:
    return Runner(
        agent=build_kbit_graph_query_agent(model_id),
        app_name=APP_NAME,
        session_service=get_graph_query_session_service(),
    )


def _as_str_list(value) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


async def build_kbit_graph_query(
    graph_id: str,
    count: int,
    *,
    model_id: str | None = None,
) -> dict | None:
    """Run the graph query agent for one graph. Returns submitted query or None."""
    user_id = require_user_id()
    runner = _get_graph_query_runner(model_id or get_default_model_id())
    session_service = get_graph_query_session_service()
    session_id = str(uuid.uuid4())

    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

    task = (
        f"Build a query for {count} knowledge bits by expanding one node "
        f"in knowledge graph {graph_id}."
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
            "Graph query agent finished without submitting",
            extra={"user_id": user_id, "graph_id": graph_id},
        )
        return None

    node_id = str(submitted.get("expansion_node_id") or "").strip()
    if not node_id:
        return None

    return {
        "include": _as_str_list(submitted.get("include")),
        "exclude": _as_str_list(submitted.get("exclude")),
        "brief": str(submitted.get("brief") or "").strip(),
        "expansion_node_id": node_id,
        "graph_id": graph_id,
    }
