"""Query strategies: work out what kind of bits the user needs right now.

``goals_profile`` and ``single_goal`` derive the query from context the
orchestrator preloaded. ``agent`` instead lets a tool-using agent read the user's
live goals, diary, calendar and existing bits and state what it finds (see
``agent.kbit_query_agent``).

Register a new algorithm by adding a class decorated with
``@QUERY_STRATEGIES.register("name")``.
"""

from __future__ import annotations

import logging

from agent.kbit_graph_query_agent import build_kbit_graph_query
from agent.kbit_query_agent import build_kbit_query
from knowledge_graph import (
    list_user_graphs,
    load_graph_snapshot,
    pick_graph,
    pick_node_by_potential,
)
from knowledge_graph.query_builder import build_graph_query

from .base import PipelineContext, Query, QueryStrategy, Registry

logger = logging.getLogger(__name__)

QUERY_STRATEGIES: Registry[QueryStrategy] = Registry("query")


def _profile_terms(profile: dict) -> list[str]:
    terms: list[str] = []
    info = (profile.get("user_information") or "").strip()
    if info:
        terms.append(info)
    return terms


def _merge_exclusions(*groups: list[str]) -> list[str]:
    """Combine exclusion lists, dropping duplicates and keeping first order."""
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for term in group:
            key = " ".join(term.lower().split())
            if key and key not in seen:
                seen.add(key)
                merged.append(term)
    return merged


@QUERY_STRATEGIES.register("goals_profile", default=True)
class GoalsProfileQuery:
    """Default: build the query from all goals plus profile background.

    Recent bit titles become exclusions so the generator avoids redundant content
    (the "state of the KB database" from the design doc).
    """

    async def build(self, ctx: PipelineContext) -> Query:
        include: list[str] = []
        for goal in ctx.goals:
            name = (goal.get("goal_name") or "").strip()
            if not name:
                continue
            description = (goal.get("goal_description") or "").strip()
            include.append(f"{name}: {description}" if description else name)

        include.extend(_profile_terms(ctx.profile))
        return Query(include=include, exclude=list(ctx.existing_titles))


@QUERY_STRATEGIES.register("single_goal")
class SingleGoalQuery:
    """Focus generation on a single goal (``ctx.goal_id``), ignoring the rest.

    Falls back to the goals+profile behaviour when no goal id is provided.
    """

    async def build(self, ctx: PipelineContext) -> Query:
        if not ctx.goal_id:
            return await GoalsProfileQuery().build(ctx)

        include: list[str] = []
        for goal in ctx.goals:
            if goal.get("id") != ctx.goal_id:
                continue
            name = (goal.get("goal_name") or "").strip()
            description = (goal.get("goal_description") or "").strip()
            if name:
                include.append(f"{name}: {description}" if description else name)

        include.extend(_profile_terms(ctx.profile))
        return Query(include=include, exclude=list(ctx.existing_titles))


@QUERY_STRATEGIES.register("agent")
class AgentQuery:
    """Let an agent read the user's live situation and state what they need.

    Richer than the preloaded strategies: the agent sees day logs, upcoming
    calendar events and how the user reacted to past bits, none of which reach
    ``PipelineContext``. Recent bit titles are merged into the exclusions either
    way, so dedup does not depend on the agent remembering them. If the agent
    never submits a query we fall back to ``goals_profile`` rather than failing
    the invoke.
    """

    async def build(self, ctx: PipelineContext) -> Query:
        submitted = await build_kbit_query(ctx.count, ctx.goal_id)
        if submitted is None:
            logger.warning("Agent query unavailable; falling back to goals_profile")
            return await GoalsProfileQuery().build(ctx)

        return Query(
            include=submitted["include"],
            exclude=_merge_exclusions(submitted["exclude"], ctx.existing_titles),
            brief=submitted["brief"],
        )


def _pick_graph_for_ctx(ctx: PipelineContext):
    """Weighted-random graph pick shared by graph query strategies."""
    graphs = list_user_graphs(ctx.user_id)
    picked = pick_graph(ctx.graph_weights, graphs)
    if picked is None:
        return None
    snapshot = load_graph_snapshot(picked["id"], ctx.user_id)
    if snapshot is None or not snapshot.nodes:
        return None
    return picked, snapshot


@QUERY_STRATEGIES.register("graph_potential")
class GraphPotentialQuery:
    """Pick a graph by weight, score nodes, and expand the highest-potential one."""

    async def build(self, ctx: PipelineContext) -> Query:
        result = _pick_graph_for_ctx(ctx)
        if result is None:
            logger.warning("graph_potential unavailable; falling back to goals_profile")
            return await GoalsProfileQuery().build(ctx)

        _graph, snapshot = result
        node = pick_node_by_potential(snapshot)
        if node is None:
            return await GoalsProfileQuery().build(ctx)
        return build_graph_query(snapshot, node, ctx)


@QUERY_STRATEGIES.register("graph_agent")
class GraphAgentQuery:
    """Pick a graph by weight, then let an agent choose the expansion node."""

    async def build(self, ctx: PipelineContext) -> Query:
        result = _pick_graph_for_ctx(ctx)
        if result is None:
            logger.warning("graph_agent unavailable; falling back to goals_profile")
            return await GoalsProfileQuery().build(ctx)

        graph, snapshot = result
        submitted = await build_kbit_graph_query(graph["id"], ctx.count)
        if submitted is None:
            node = pick_node_by_potential(snapshot)
            if node is None:
                return await GoalsProfileQuery().build(ctx)
            return build_graph_query(snapshot, node, ctx)

        expansion_node_id = str(submitted.get("expansion_node_id") or "").strip()
        if snapshot.node_by_id(expansion_node_id) is None:
            logger.warning(
                "Graph agent returned unknown expansion node; falling back to potential pick",
                extra={
                    "graph_id": graph["id"],
                    "expansion_node_id": expansion_node_id,
                },
            )
            node = pick_node_by_potential(snapshot)
            if node is None:
                return await GoalsProfileQuery().build(ctx)
            return build_graph_query(snapshot, node, ctx)

        ctx.selected_graph_id = graph["id"]
        ctx.selected_node_id = expansion_node_id
        return Query(
            include=submitted["include"],
            exclude=_merge_exclusions(submitted["exclude"], ctx.existing_titles),
            brief=submitted["brief"],
            graph_id=graph["id"],
            expansion_node_id=expansion_node_id,
        )
