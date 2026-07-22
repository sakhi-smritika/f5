"""Knowledge-bits generation pipeline.

Four strategy stages, each with a registry and a default:

- ``QUERY_STRATEGIES``  -> build a :class:`Query` from user context
- ``SOURCE_STRATEGIES`` -> fetch candidate bits (the Source of Knowledge)
- ``SCREEN_STRATEGIES`` -> drop unwanted candidates
- ``RANK_STRATEGIES``   -> order candidates best-first

Use :func:`invoke_kbits` to run all four and persist the result.
"""

from .base import KBCandidate, PipelineContext, Query, Registry
from .orchestrator import build_context, invoke_kbits
from .query import QUERY_STRATEGIES
from .ranker import RANK_STRATEGIES
from .screener import SCREEN_STRATEGIES
from .sources import SOURCE_STRATEGIES

STRATEGY_REGISTRIES = {
    "query": QUERY_STRATEGIES,
    "source": SOURCE_STRATEGIES,
    "screen": SCREEN_STRATEGIES,
    "rank": RANK_STRATEGIES,
}

__all__ = [
    "KBCandidate",
    "PipelineContext",
    "Query",
    "Registry",
    "QUERY_STRATEGIES",
    "SOURCE_STRATEGIES",
    "SCREEN_STRATEGIES",
    "RANK_STRATEGIES",
    "STRATEGY_REGISTRIES",
    "build_context",
    "invoke_kbits",
]
