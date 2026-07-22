"""Screen strategies: drop unwanted candidates before ranking.

Text-only for now. Embedding-based screening can be added later as another
registered strategy without changing the contract.
"""

from __future__ import annotations

from .base import KBCandidate, PipelineContext, Registry, ScreenStrategy

SCREEN_STRATEGIES: Registry[ScreenStrategy] = Registry("screen")


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


@SCREEN_STRATEGIES.register("text", default=True)
class TextScreener:
    """Default: drop empty bits and near-duplicates by normalized title.

    Deduplicates within the batch and against the user's existing bit titles
    (``ctx.existing_titles``) to avoid redundant content.
    """

    def screen(
        self, candidates: list[KBCandidate], ctx: PipelineContext
    ) -> list[KBCandidate]:
        seen = {_normalize(title) for title in ctx.existing_titles}
        kept: list[KBCandidate] = []
        for candidate in candidates:
            title = candidate.title.strip()
            content = candidate.content.strip()
            if not title or not content:
                continue
            key = _normalize(title)
            if key in seen:
                continue
            seen.add(key)
            kept.append(candidate)
        return kept


@SCREEN_STRATEGIES.register("noop")
class NoopScreener:
    """Pass every candidate through unchanged."""

    def screen(
        self, candidates: list[KBCandidate], ctx: PipelineContext
    ) -> list[KBCandidate]:
        return list(candidates)
