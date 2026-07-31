"""Compose the four strategy stages into a single invoke run.

``invoke_kbits`` loads the shared context once, resolves each stage's strategy by
name (falling back to the registered default), runs
build -> generate -> screen -> rank, then inserts the results.
"""

from __future__ import annotations

import logging
import uuid

from tools.context import current_user_id
from config.supabase import get_supabase_service_client

from .base import KBCandidate, PipelineContext
from .generators import GENERATOR_STRATEGIES, build_generator_user_message
from .query import QUERY_STRATEGIES
from .ranker import RANK_STRATEGIES
from .screener import SCREEN_STRATEGIES

from ..access import KBIT_COLUMNS

logger = logging.getLogger(__name__)

_GOAL_COLUMNS = "id, goal_name, goal_description, progress, parent_goal"
_PROFILE_COLUMNS = "full_name, user_information"


def _load_goals(user_id: str) -> list[dict]:
    result = (
        get_supabase_service_client()
        .table("goals")
        .select(_GOAL_COLUMNS)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return result.data or []


def _load_profile(user_id: str) -> dict:
    result = (
        get_supabase_service_client()
        .table("users")
        .select(_PROFILE_COLUMNS)
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else {}


def build_context(user_id: str, goal_id: str | None, count: int) -> PipelineContext:
    """Load goals, profile, and existing titles once for the whole run."""
    from ..access import fetch_recent_titles

    return PipelineContext(
        user_id=user_id,
        goal_id=goal_id,
        count=count,
        goals=_load_goals(user_id),
        profile=_load_profile(user_id),
        existing_titles=fetch_recent_titles(user_id),
    )


async def invoke_kbits(
    user_id: str,
    *,
    goal_id: str | None = None,
    count: int = 5,
    query_strategy: str | None = None,
    generator_strategy: str | None = None,
    screen_strategy: str | None = None,
    rank_strategy: str | None = None,
) -> list[dict]:
    """Run the pipeline end to end and persist the resulting bits.

    Raises ``KeyError`` if any strategy name is unknown (mapped to 422 upstream).
    """
    query_algo = QUERY_STRATEGIES.get(query_strategy)
    generator_algo = GENERATOR_STRATEGIES.get(generator_strategy)
    screen_algo = SCREEN_STRATEGIES.get(screen_strategy)
    rank_algo = RANK_STRATEGIES.get(rank_strategy)

    ctx = build_context(user_id, goal_id, count)

    # Agent-backed strategies run tools that read the signed-in user from this
    # context var rather than taking a user id argument, so the model can never
    # reach another user's data.
    token = current_user_id.set(user_id)
    try:
        query = await query_algo.build(ctx)
        generator_prompt = build_generator_user_message(query, count)
        candidates = await generator_algo.generate(query, count)
    finally:
        current_user_id.reset(token)

    candidates = screen_algo.screen(candidates, ctx)
    candidates = rank_algo.rank(candidates, query)
    candidates = candidates[:count]

    if not candidates:
        logger.info("Invoke produced no bits", extra={"user_id": user_id})
        return []

    return _persist(user_id, goal_id, candidates, generator_prompt=generator_prompt)


def _persist(
    user_id: str,
    goal_id: str | None,
    candidates: list[KBCandidate],
    *,
    generator_prompt: str | None = None,
) -> list[dict]:
    """Insert candidates as knowledge_bits rows and return the stored rows."""
    rows = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": candidate.title,
            "content": candidate.content,
            "related_goal": goal_id,
            "generator_prompt": generator_prompt,
        }
        for candidate in candidates
    ]
    result = (
        get_supabase_service_client()
        .table("knowledge_bits")
        .insert(rows)
        .select(KBIT_COLUMNS)
        .execute()
    )
    logger.info(
        "Invoke inserted bits",
        extra={"user_id": user_id, "count": len(rows)},
    )
    return result.data or rows
