"""Query strategies: turn user context into a ``Query`` (include/exclude terms).

Register a new algorithm by adding a class decorated with
``@QUERY_STRATEGIES.register("name")``.
"""

from __future__ import annotations

from .base import PipelineContext, Query, QueryStrategy, Registry

QUERY_STRATEGIES: Registry[QueryStrategy] = Registry("query")


def _profile_terms(profile: dict) -> list[str]:
    terms: list[str] = []
    info = (profile.get("user_information") or "").strip()
    if info:
        terms.append(info)
    return terms


@QUERY_STRATEGIES.register("goals_profile", default=True)
class GoalsProfileQuery:
    """Default: build the query from all goals plus profile background.

    Recent bit titles become exclusions so the source avoids redundant content
    (the "state of the KB database" from the design doc).
    """

    def build(self, ctx: PipelineContext) -> Query:
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

    def build(self, ctx: PipelineContext) -> Query:
        if not ctx.goal_id:
            return GoalsProfileQuery().build(ctx)

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
