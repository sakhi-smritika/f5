from fastapi import APIRouter

from .bits import router as bits_router
from .invoke import router as invoke_router

router = APIRouter()
# Include invoke first so static paths (/strategies, /invoke) resolve before the
# dynamic /{kbit_id} route in bits. Both sub-routers carry the /kbits prefix.
router.include_router(invoke_router)
router.include_router(bits_router)
