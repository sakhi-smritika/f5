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
from config.pings import (
    check_supabase_connection,
    check_supabase_service_key,
    check_openai_api_key,
    check_gemini_api_key,
    check_database_connection,
)


load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
PING = os.getenv("PING", "false")

def _run_startup_checks() -> None:
    if SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY:
        check_supabase_connection(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
    if SUPABASE_URL and SUPABASE_SECRET_KEY:
        check_supabase_service_key(SUPABASE_URL, SUPABASE_SECRET_KEY)
    if OPENAI_API_KEY:
        check_openai_api_key(OPENAI_API_KEY)
    if GEMINI_API_KEY:
        check_gemini_api_key(GEMINI_API_KEY)
    if DATABASE_URL:
        check_database_connection(DATABASE_URL)

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
        _run_startup_checks()
    else:
        logger.info("Skipping startup checks because PING is false")
    

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
