"""
Third-party integration endpoints (OAuth, connection status, etc.).

Each integration lives in its own module; this package composes their routers
under ``/api/v1/integrations``.
"""

from .google_workspace import callback_router as google_callback_router
from .router import router

__all__ = ["router", "google_callback_router"]
