from fastapi import APIRouter

from .attachments import router as attachments_router
from .conversations import router as conversations_router
from .folders import router as folders_router
from .messages import router as messages_router

router = APIRouter(prefix="/chat", tags=["chat"])
router.include_router(conversations_router)
router.include_router(messages_router)
router.include_router(attachments_router)
router.include_router(folders_router)
