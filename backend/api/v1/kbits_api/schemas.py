"""Request bodies for the Knowledge Bits API.

Strategy names are optional on ``InvokeBody``; when omitted, each pipeline stage
falls back to its registered default (see ``pipeline``).
"""

from pydantic import BaseModel


class InvokeBody(BaseModel):
    """Body for ``POST /kbits/invoke``.

    ``goal_id`` optionally focuses generation on a single goal. The four
    ``*_strategy`` fields select the algorithm for each pipeline stage; leave
    them unset to use the stage default.
    """

    goal_id: str | None = None
    count: int | None = None
    query_strategy: str | None = None
    generator_strategy: str | None = None
    screen_strategy: str | None = None
    rank_strategy: str | None = None


class UpdateKbitBody(BaseModel):
    """Body for ``PATCH /kbits/{id}`` — interaction flags only."""

    is_read: bool | None = None
    is_liked: bool | None = None
    is_disliked: bool | None = None
    rating: int | None = None
    is_marked_relavant: bool | None = None
    is_marked_irrelavant: bool | None = None
