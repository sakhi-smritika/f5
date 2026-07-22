import logging

from fastapi import APIRouter, Depends, Request

from api.v1.chat_api import router as chat_router
from api.v1.integrations import router as integrations_router
from api.v1.kbits_api import router as kbits_router
from api.v1.models import router as models_router
from config.auth import AuthenticatedUser, get_current_user

logger = logging.getLogger(__name__)

router : APIRouter = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)

router.include_router(chat_router)
router.include_router(integrations_router)
router.include_router(kbits_router)
router.include_router(models_router)


@router.get("/hello")
def hello(request: Request, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """
    A sample hello endpoint.
    """
    logger.info("Hello endpoint called", extra={"user_id": user.id})
    return {
        "message": "hello",
        "user_id": user.id,
    }
