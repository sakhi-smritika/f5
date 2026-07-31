"""Knowledge-bits generation pipeline.

Four strategy stages, each with a registry and a default:

- ``QUERY_STRATEGIES``     -> work out what kind of bits the user needs
- ``GENERATOR_STRATEGIES`` -> produce candidate bits for that query
- ``SCREEN_STRATEGIES``    -> drop unwanted candidates
- ``RANK_STRATEGIES``      -> order candidates best-first

Use :func:`invoke_kbits` to run all four and persist the result.
"""

from .base import KBCandidate, PipelineContext, Query, Registry
from .generators import GENERATOR_STRATEGIES
from .orchestrator import build_context, invoke_kbits, resolve_strategies
from .query import QUERY_STRATEGIES
from .ranker import RANK_STRATEGIES
from .screener import SCREEN_STRATEGIES

STRATEGY_REGISTRIES = {
    "query": QUERY_STRATEGIES,
    "generator": GENERATOR_STRATEGIES,
    "screen": SCREEN_STRATEGIES,
    "rank": RANK_STRATEGIES,
}

__all__ = [
    "KBCandidate",
    "PipelineContext",
    "Query",
    "Registry",
    "QUERY_STRATEGIES",
    "GENERATOR_STRATEGIES",
    "SCREEN_STRATEGIES",
    "RANK_STRATEGIES",
    "STRATEGY_REGISTRIES",
    "build_context",
    "invoke_kbits",
    "resolve_strategies",
]
