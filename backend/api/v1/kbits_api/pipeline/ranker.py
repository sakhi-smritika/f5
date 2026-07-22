"""Rank strategies: order screened candidates best-first.

Text-only for now. An embedding-similarity ranker can be added later as another
registered strategy without changing the contract.
"""

from __future__ import annotations

import re

from .base import KBCandidate, Query, RankStrategy, Registry

RANK_STRATEGIES: Registry[RankStrategy] = Registry("rank")

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


@RANK_STRATEGIES.register("text", default=True)
class TextRanker:
    """Default: score by keyword overlap with the query's include terms."""

    def rank(self, candidates: list[KBCandidate], query: Query) -> list[KBCandidate]:
        include_tokens = _tokens(" ".join(query.include))
        if not include_tokens:
            return list(candidates)

        def score(candidate: KBCandidate) -> int:
            bit_tokens = _tokens(f"{candidate.title} {candidate.content}")
            return len(include_tokens & bit_tokens)

        return sorted(candidates, key=score, reverse=True)


@RANK_STRATEGIES.register("noop")
class NoopRanker:
    """Preserve the source order."""

    def rank(self, candidates: list[KBCandidate], query: Query) -> list[KBCandidate]:
        return list(candidates)
