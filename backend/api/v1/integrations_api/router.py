from fastapi import APIRouter

from .google_workspace import router as google_workspace_router

router = APIRouter(prefix="/integrations", tags=["integrations"])
router.include_router(google_workspace_router)
