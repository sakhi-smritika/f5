"""Generation endpoints: run the pipeline and expose available strategies."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from config.auth import AuthenticatedUser, get_current_user

from .constants import DEFAULT_INVOKE_COUNT, MAX_INVOKE_COUNT
from .pipeline import STRATEGY_REGISTRIES, invoke_kbits
from .schemas import InvokeBody

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kbits", tags=["kbits"])


@router.get("/strategies")
def list_strategies() -> dict:
    """List available strategies per pipeline stage and each stage's default.

    Lets the frontend offer strategy selection without hardcoding names.
    """
    return {
        stage: {"default": registry.default, "options": registry.names()}
        for stage, registry in STRATEGY_REGISTRIES.items()
    }


@router.post("/invoke")
async def invoke(
    body: InvokeBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Generate knowledge bits for the signed-in user and persist them.

    Each ``*_strategy`` field is optional; omit it to use the stage default.
    """
    count = body.count or DEFAULT_INVOKE_COUNT
    count = max(1, min(count, MAX_INVOKE_COUNT))

    try:
        bits = await invoke_kbits(
            user.id,
            goal_id=body.goal_id,
            count=count,
            query_strategy=body.query_strategy,
            generator_strategy=body.generator_strategy,
            screen_strategy=body.screen_strategy,
            rank_strategy=body.rank_strategy,
        )
    except (KeyError, LookupError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc).strip('"'),
        )

    return {"count": len(bits), "bits": bits}
