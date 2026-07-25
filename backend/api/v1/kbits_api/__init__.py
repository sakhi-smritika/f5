"""
Knowledge Bits (kbits) API.

Serves readable, goal-relevant knowledge snippets the user consumes instead of
doom-scrolling. Bits live in ``public.knowledge_bits``. New bits are produced by
a four-stage strategy pipeline (query -> generate -> screen -> rank); see
``pipeline`` for the interchangeable algorithms behind each stage.
"""

from .router import router

__all__ = ["router"]
