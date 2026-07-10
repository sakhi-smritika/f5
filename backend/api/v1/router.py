import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
)


@router.get("/hello")
def hello(_: Request) -> dict:
    """
    A sample hello endpoint.
    """
    logger.info("Hello endpoint called")
    return {
        "message": "hello"
    }
