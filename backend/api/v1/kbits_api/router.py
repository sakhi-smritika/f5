from fastapi import APIRouter

from .bits import router as bits_router
from .discussion import router as discussion_router
from .invoke import router as invoke_router

router = APIRouter()
# Include invoke first so static paths (/strategies, /invoke) resolve before the
# dynamic /{kbit_id} route in bits. The discussion router owns the two-segment
# /{kbit_id}/discussion path, which never collides with bits' /{kbit_id}. All
# sub-routers carry the /kbits prefix.
router.include_router(invoke_router)
router.include_router(discussion_router)
router.include_router(bits_router)
