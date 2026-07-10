"""
Exposes the function to create the FastAPI application instance. To be used by main.py
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1.router import router as v1_router
from config.logger import setup_logging
from config.middleware import RequestLoggingMiddleware

load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application starting")
    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """
    The function to create the FastAPI application instance. To be used by main.py
    """
    setup_logging()

    app = FastAPI(title="My Sakhismritika Application", lifespan=lifespan)
    environment = os.getenv("ENVIRONMENT", "local") 
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if environment == "local":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[origin.strip() for origin in cors_origins if origin.strip()],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://sakhismritika.space", "https://www.sakhismritika.space"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(v1_router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error_type": type(exc).__name__,
            },
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app
