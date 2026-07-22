"""Feed and interaction endpoints for knowledge bits."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from config.auth import AuthenticatedUser, get_current_user
from config.supabase import get_supabase_service_client

from .access import get_owned_kbit, list_kbits
from .constants import MAX_RATING, MIN_RATING, UPDATABLE_FIELDS
from .schemas import UpdateKbitBody

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kbits", tags=["kbits"])


@router.get("")
def get_feed(
    is_read: bool | None = Query(default=None),
    related_goal: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Return the user's knowledge-bit feed, newest first."""
    bits = list_kbits(
        user.id,
        is_read=is_read,
        related_goal=related_goal,
        limit=limit,
        offset=offset,
    )
    return {"count": len(bits), "bits": bits}


@router.get("/{kbit_id}")
def get_kbit(
    kbit_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Return a single knowledge bit by id."""
    return get_owned_kbit(kbit_id, user.id)


@router.patch("/{kbit_id}")
def update_kbit(
    kbit_id: str,
    body: UpdateKbitBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Update interaction flags (read/like/dislike/rating/relevance) on a bit."""
    get_owned_kbit(kbit_id, user.id)

    updates = {
        field: value
        for field, value in body.model_dump(exclude_unset=True).items()
        if field in UPDATABLE_FIELDS
    }
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No updatable fields provided",
        )

    rating = updates.get("rating")
    if rating is not None and not (MIN_RATING <= rating <= MAX_RATING):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"rating must be between {MIN_RATING} and {MAX_RATING}",
        )

    get_supabase_service_client().table("knowledge_bits").update(updates).eq(
        "id", kbit_id
    ).eq("user_id", user.id).execute()

    return {"id": kbit_id, **updates}


@router.delete("/{kbit_id}")
def delete_kbit(
    kbit_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Delete a knowledge bit."""
    get_owned_kbit(kbit_id, user.id)
    get_supabase_service_client().table("knowledge_bits").delete().eq(
        "id", kbit_id
    ).eq("user_id", user.id).execute()
    return {"ok": True}
