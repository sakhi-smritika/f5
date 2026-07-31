"""Compose the four strategy stages into a single invoke run.

``invoke_kbits`` loads the shared context once, resolves each stage's strategy by
name (falling back to the registered default), runs
build -> generate -> screen -> rank, then inserts the results.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, replace

from knowledge_graph.constants import GRAPH_QUERY_STRATEGIES
from knowledge_graph.enrichment import enrich_persisted_bits
from knowledge_graph.store import count_user_graphs, load_graph_snapshot, mark_node_expanded
from tools.context import current_user_id
from config.supabase import get_supabase_service_client

from .base import KBCandidate, PipelineContext
from .generators import GENERATOR_STRATEGIES, build_generator_user_message
from .query import QUERY_STRATEGIES
from .ranker import RANK_STRATEGIES
from .resolver import resolve_stage_strategy
from .screener import SCREEN_STRATEGIES

from ..access import KBIT_COLUMNS

logger = logging.getLogger(__name__)

_GOAL_COLUMNS = "id, goal_name, goal_description, progress, parent_goal"
_PROFILE_COLUMNS = "full_name, user_information"


@dataclass
class ResolvedStrategies:
    query: str
    generator: str
    screen: str
    rank: str


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


def build_context(
    user_id: str,
    goal_id: str | None,
    count: int,
    *,
    graph_weights: dict[str, float] | None = None,
) -> PipelineContext:
    """Load goals, profile, and existing titles once for the whole run."""
    from ..access import fetch_recent_titles

    return PipelineContext(
        user_id=user_id,
        goal_id=goal_id,
        count=count,
        goals=_load_goals(user_id),
        profile=_load_profile(user_id),
        existing_titles=fetch_recent_titles(user_id),
        graph_weights=graph_weights or {},
    )


def resolve_strategies(
    user_id: str,
    *,
    query_strategy: str | None = None,
    generator_strategy: str | None = None,
    screen_strategy: str | None = None,
    rank_strategy: str | None = None,
    strategy_weights: dict[str, dict[str, float]] | None = None,
) -> ResolvedStrategies:
    """Resolve each pipeline stage by explicit override or weighted random."""
    weights = strategy_weights or {}
    query_exclude: set[str] | None = None
    if count_user_graphs(user_id) == 0:
        query_exclude = set(GRAPH_QUERY_STRATEGIES)

    return ResolvedStrategies(
        query=resolve_stage_strategy(
            QUERY_STRATEGIES,
            query_strategy,
            weights.get("query"),
            exclude=query_exclude,
        ),
        generator=resolve_stage_strategy(
            GENERATOR_STRATEGIES,
            generator_strategy,
            weights.get("generator"),
        ),
        screen=resolve_stage_strategy(
            SCREEN_STRATEGIES,
            screen_strategy,
            weights.get("screen"),
        ),
        rank=resolve_stage_strategy(
            RANK_STRATEGIES,
            rank_strategy,
            weights.get("rank"),
        ),
    )


def _build_base_metadata(resolved: ResolvedStrategies, query, ctx: PipelineContext) -> dict:
    metadata: dict = {
        "query_strategy": resolved.query,
        "generator_strategy": resolved.generator,
        "screen_strategy": resolved.screen,
        "rank_strategy": resolved.rank,
    }
    if query.graph_id:
        snapshot = load_graph_snapshot(query.graph_id, ctx.user_id)
        if snapshot:
            metadata["graph"] = {"id": snapshot.id, "title": snapshot.title}
    if query.expansion_node_id and query.graph_id:
        snapshot = load_graph_snapshot(query.graph_id, ctx.user_id)
        if snapshot:
            node = snapshot.node_by_id(query.expansion_node_id)
            if node:
                metadata["expansion_node"] = {"id": node.id, "label": node.label}
    return metadata


async def invoke_kbits(
    user_id: str,
    *,
    goal_id: str | None = None,
    count: int = 5,
    query_strategy: str | None = None,
    generator_strategy: str | None = None,
    screen_strategy: str | None = None,
    rank_strategy: str | None = None,
    strategy_weights: dict[str, dict[str, float]] | None = None,
    graph_weights: dict[str, float] | None = None,
) -> list[dict]:
    """Run the pipeline end to end and persist the resulting bits.

    Raises ``KeyError`` if any strategy name is unknown (mapped to 422 upstream).
    """
    resolved = resolve_strategies(
        user_id,
        query_strategy=query_strategy,
        generator_strategy=generator_strategy,
        screen_strategy=screen_strategy,
        rank_strategy=rank_strategy,
        strategy_weights=strategy_weights,
    )

    query_algo = QUERY_STRATEGIES.get(resolved.query)
    generator_algo = GENERATOR_STRATEGIES.get(resolved.generator)
    screen_algo = SCREEN_STRATEGIES.get(resolved.screen)
    rank_algo = RANK_STRATEGIES.get(resolved.rank)

    ctx = build_context(user_id, goal_id, count, graph_weights=graph_weights)

    token = current_user_id.set(user_id)
    raw_candidates: list[KBCandidate] = []
    try:
        query = await query_algo.build(ctx)
        generator_prompt = build_generator_user_message(query, count)
        raw_candidates = await generator_algo.generate(query, count)
        candidates = screen_algo.screen(raw_candidates, ctx)

        if not candidates and raw_candidates:
            rejected = [candidate.title for candidate in raw_candidates if candidate.title.strip()]
            logger.warning(
                "All generated bits were screened as duplicates; retrying generator",
                extra={
                    "user_id": user_id,
                    "generated_count": len(raw_candidates),
                    "rejected_titles": rejected[:10],
                },
            )
            retry_query = replace(query, rejected_titles=rejected)
            generator_prompt = build_generator_user_message(retry_query, count)
            raw_candidates = await generator_algo.generate(retry_query, count)
            candidates = screen_algo.screen(raw_candidates, ctx)
    finally:
        current_user_id.reset(token)

    candidates = rank_algo.rank(candidates, query)
    candidates = candidates[:count]

    base_metadata = _build_base_metadata(resolved, query, ctx)

    if not candidates:
        logger.info(
            "Invoke produced no bits",
            extra={
                "user_id": user_id,
                "invoke_metadata": base_metadata,
                "reason": (
                    "all_duplicates_after_retry"
                    if raw_candidates
                    else "generator_empty_or_unparseable"
                ),
            },
        )
        return []

    rows = _persist(user_id, goal_id, candidates, generator_prompt=generator_prompt)
    _patch_bits_metadata(rows, base_metadata)

    if query.graph_id:
        snapshot = load_graph_snapshot(query.graph_id, user_id)
        expansion_node_id = query.expansion_node_id
        if snapshot and expansion_node_id and snapshot.node_by_id(expansion_node_id):
            mark_node_expanded(expansion_node_id, increment_kbit_count=len(rows))
            await enrich_persisted_bits(
                snapshot=snapshot,
                expansion_node_id=expansion_node_id,
                bits=rows,
                base_metadata=base_metadata,
            )
        elif snapshot and expansion_node_id:
            logger.warning(
                "Skipping graph enrichment for unknown expansion node",
                extra={
                    "user_id": user_id,
                    "graph_id": query.graph_id,
                    "expansion_node_id": expansion_node_id,
                },
            )

    return rows


def _patch_bits_metadata(bits: list[dict], metadata: dict) -> None:
    from knowledge_graph.store import patch_bit_metadata

    for bit in bits:
        patch_bit_metadata(bit["id"], metadata)
        bit["metadata"] = metadata


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
