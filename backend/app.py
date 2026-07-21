"""
Exposes the function to create the FastAPI application instance. To be used by main.py
"""

import logging
import os
import json
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1.integrations import callback_router as google_callback_router
from api.v1.router import router as v1_router
from config.logger import setup_logging
from config.middleware import RequestLoggingMiddleware
from config.llm_keys import PROVIDER_ENV_KEYS, get_model_provider
from config.models import get_available_models
from config.pings import Pings

load_dotenv()

logger = logging.getLogger(__name__)


PING = os.getenv("PING", "false")


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
    if PING.lower() == "true":
        logger.info("Running startup checks because PING is true")
        for attr_name in dir(Pings):
            if attr_name.startswith("ping_") and callable(getattr(Pings, attr_name)):
                try:
                    getattr(Pings, attr_name)()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning(
                        "Startup ping failed",
                        extra={
                            "ping_name": attr_name,
                            "error": str(exc),
                        },
                    )
    else:
        logger.info("Skipping startup checks because PING is false")
    

    app = FastAPI(title="My Sakhismritika Application", lifespan=lifespan)
    environment = os.getenv("ENVIRONMENT", "local")
    raw_cors = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    try:
        if raw_cors.strip().startswith("["):
            cors_origins = json.loads(raw_cors)
        else:
            cors_origins = [o.strip() for o in raw_cors.split(",") if o.strip()]
    except Exception:
        cors_origins = [o.strip() for o in raw_cors.replace("[", "").replace("]", "").replace('"', "").split(",") if o.strip()]

    if environment == "local":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[origin for origin in cors_origins],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(f"Local environment detected. CORS origins set to: {cors_origins}")
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
    app.include_router(google_callback_router)

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
