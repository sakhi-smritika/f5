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
from config.pings import (
    check_anthropic_api_key,
    check_supabase_connection,
    check_supabase_service_key,
    check_openai_api_key,
    check_gemini_api_key,
    check_database_connection,
    check_google_token_enc_key,
    check_google_oauth_flow,
    check_google_oauth_client,
    check_google_connections_table,
)


load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_OAUTH_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
GOOGLE_TOKEN_ENC_KEY = os.getenv("GOOGLE_TOKEN_ENC_KEY")
PING = os.getenv("PING", "false")

def _run_startup_checks() -> None:
    if SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY:
        check_supabase_connection(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
    else:
        logger.error("SUPABASE_URL and/or SUPABASE_PUBLISHABLE_KEY are not set")

    if SUPABASE_URL and SUPABASE_SECRET_KEY:
        check_supabase_service_key(SUPABASE_URL, SUPABASE_SECRET_KEY)
    else:
        logger.error("SUPABASE_URL and/or SUPABASE_SECRET_KEY are not set")

    provider_key_checks = {
        "openai": (OPENAI_API_KEY, check_openai_api_key),
        "gemini": (GEMINI_API_KEY, check_gemini_api_key),
        "anthropic": (ANTHROPIC_API_KEY, check_anthropic_api_key),
    }
    required_providers = {
        get_model_provider(model.id) for model in get_available_models()
    }
    for provider in sorted(required_providers):
        env_key = PROVIDER_ENV_KEYS[provider]
        api_key, check_fn = provider_key_checks[provider]
        if api_key:
            check_fn(api_key)
        else:
            logger.warning(
                "%s is not set but is required for CHAT_MODELS provider %s",
                env_key,
                provider,
            )

    if DATABASE_URL:
        check_database_connection(DATABASE_URL)
    else:
        logger.error("DATABASE_URL is not set")

    google_vars = {
        "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
        "GOOGLE_OAUTH_REDIRECT_URI": GOOGLE_OAUTH_REDIRECT_URI,
        "GOOGLE_TOKEN_ENC_KEY": GOOGLE_TOKEN_ENC_KEY,
    }
    missing_google = [name for name, value in google_vars.items() if not value]
    if missing_google:
        logger.warning(
            "Skipping Google integration checks; missing: %s",
            ", ".join(missing_google),
        )
    else:
        check_google_token_enc_key(GOOGLE_TOKEN_ENC_KEY)
        check_google_oauth_flow(
            GOOGLE_CLIENT_ID,
            GOOGLE_CLIENT_SECRET,
            GOOGLE_OAUTH_REDIRECT_URI,
        )
        check_google_oauth_client(
            GOOGLE_CLIENT_ID,
            GOOGLE_CLIENT_SECRET,
            GOOGLE_OAUTH_REDIRECT_URI,
        )
        if SUPABASE_URL and SUPABASE_SECRET_KEY:
            check_google_connections_table(SUPABASE_URL, SUPABASE_SECRET_KEY)
        else:
            logger.error(
                "Skipping google_connections table check; "
                "SUPABASE_URL and/or SUPABASE_SECRET_KEY are not set"
            )

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
