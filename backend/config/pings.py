# pylint: disable=broad-exception-caught
"""
Module Exposes a function to test if all API and SECURE KEYs are work
"""

import asyncio
import functools
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from cryptography.fernet import Fernet, InvalidToken
from google import genai
from google_auth_oauthlib.flow import Flow
from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from supabase import create_client

from config.google_oauth import GOOGLE_SCOPES

logger = logging.getLogger(__name__)


def with_retries(retries: int = 5, initial_delay: float = 1.0):
    """Decorator to retry a function with exponential backoff."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exc = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt < retries - 1:
                        logger.warning(
                            "Retry attempt failed",
                            extra={
                                "function_name": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": retries,
                                "error": str(e),
                                "retry_delay_seconds": delay,
                            },
                        )
                        time.sleep(delay)
                        delay = min(delay * 2, 16.0)
            logger.error(
                "Function failed after all retries",
                extra={
                    "function_name": func.__name__,
                    "max_retries": retries,
                    "final_error": str(last_exc),
                },
            )
            return False

        return wrapper

    return decorator


@with_retries(retries=5)
def check_gemini_api_key(gemini_key):
    """To Check if Gemini Key works"""
    try:
        client = genai.Client(api_key=gemini_key)

        response = client.models.generate_content(model="gemini-2.5-flash", contents="Are you working?")
        logger.info(
            "Gemini API key check passed",
            extra={
                "status": "success",
                "response_preview": response.text[:10] if response.text else None,
            },
        )
        return True

    except Exception as e:
        logger.error(
            "Gemini API key check failed",
            extra={
                "status": "failure",
                "error": str(e),
            },
        )
        raise


@with_retries(retries=5)
def check_openai_api_key(openai_key) -> bool:
    """To Check if OPENAI API KEY works"""
    try:
        client = OpenAI(api_key=openai_key)  # picks OPENAI_API_KEY from env

        resp = client.responses.create(model="gpt-4.1-mini", input="Say OK")

        logger.info(
            "OpenAI API key check passed",
            extra={
                "status": "success",
                "response_preview": resp.output_text[:10] if resp.output_text else None,
            },
        )
        return True

    except Exception as e:
        logger.error(
            "OpenAI API key check failed",
            extra={
                "status": "failure",
                "error": str(e),
            },
        )
        raise


@with_retries(retries=5)
def check_supabase_connection(supabase_url, supabase_anon_key) -> bool:
    """To check if SUPABASE_URL and SUPABASE_ANON_KEY works"""
    try:
        headers = {
            "apikey": supabase_anon_key,
            "Authorization": f"Bearer {supabase_anon_key}",
        }

        r = requests.get(f"{supabase_url}/rest/v1/", headers=headers, timeout=5)

        # 401 = key accepted but no resource (EXPECTED)
        if r.status_code in (200, 401, 404):
            logger.info(
                "Supabase connection check passed",
                extra={
                    "status": "success",
                    "http_status_code": r.status_code,
                },
            )
            return True
        raise RuntimeError(f"Unexpected status code: {r.status_code}")

    except Exception as e:
        logger.error(
            "Supabase connection check failed",
            extra={
                "status": "failure",
                "error": str(e),
            },
        )
        raise


@with_retries(retries=5)
def check_supabase_service_key(supabase_url, service_key) -> bool:
    """To check if SUPABASE_SERVICE_KEY works"""
    try:
        supabase = create_client(supabase_url, service_key)

        # Service key must bypass RLS
        # This query should succeed even if RLS is enabled
        supabase.table("users").select("id").limit(1).execute()
        logger.info(
            "Supabase service key check passed",
            extra={
                "status": "success",
            },
        )
        return True

    except Exception as e:
        logger.error(
            "Supabase service key check failed",
            extra={
                "status": "failure",
                "error": str(e),
            },
        )
        raise

@with_retries(retries=5)
def check_database_connection(database_url) -> bool:
    """To check if DATABASE_URL works for ADK's DatabaseSessionService.

    ADK builds its session store with ``create_async_engine(DATABASE_URL)``, so the URL
    must use an async driver (e.g. ``postgresql+asyncpg://user:pass@host:5432/postgres``).
    Any URL/driver/connectivity problem is what ADK later re-raises as a ValueError on the
    first chat request, so we mirror it here and actually open a connection to surface it
    at startup instead.
    """
    try:
        async def _probe() -> None:
            engine = create_async_engine(database_url, pool_pre_ping=True)
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            finally:
                await engine.dispose()

        # Run in a dedicated thread with its own event loop so this works whether or
        # not the caller is already inside a running event loop (asyncio.run() would
        # raise "cannot be called from a running event loop").
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(asyncio.run, _probe()).result()

        logger.info(
            "Database connection check passed",
            extra={
                "status": "success",
            },
        )
        return True

    except Exception as e:
        logger.error(
            "Database connection check failed",
            extra={
                "status": "failure",
                "error": str(e),
            },
        )
        raise


@with_retries(retries=5)
def check_google_token_enc_key(token_enc_key: str) -> bool:
    """Verify GOOGLE_TOKEN_ENC_KEY is a valid Fernet key and can round-trip."""
    try:
        fernet = Fernet(token_enc_key.encode())
        sample = "startup-ping-google-refresh-token"
        encrypted = fernet.encrypt(sample.encode()).decode()
        decrypted = fernet.decrypt(encrypted.encode()).decode()
        if decrypted != sample:
            raise RuntimeError("Fernet round-trip mismatch")

        logger.info(
            "Google token encryption key check passed",
            extra={"status": "success"},
        )
        return True

    except (InvalidToken, ValueError) as e:
        logger.error(
            "Google token encryption key check failed",
            extra={
                "status": "failure",
                "error": (
                    f"{e}. Generate a valid key with: "
                    'python -c "from cryptography.fernet import Fernet; '
                    'print(Fernet.generate_key().decode())"'
                ),
            },
        )
        raise


@with_retries(retries=5)
def check_google_oauth_flow(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> bool:
    """Verify OAuth client config can build a consent URL."""
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=GOOGLE_SCOPES,
        )
        flow.redirect_uri = redirect_uri
        auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
        if not auth_url.startswith("https://accounts.google.com/o/oauth2/auth"):
            raise RuntimeError(f"Unexpected authorization URL: {auth_url[:80]}")

        logger.info(
            "Google OAuth flow check passed",
            extra={
                "status": "success",
                "redirect_uri": redirect_uri,
            },
        )
        return True

    except Exception as e:
        logger.error(
            "Google OAuth flow check failed",
            extra={
                "status": "failure",
                "error": str(e),
            },
        )
        raise


@with_retries(retries=5)
def check_google_oauth_client(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> bool:
    """Probe Google's token endpoint to confirm client id/secret are accepted.

    We intentionally exchange a bogus authorization code. Google should answer
    with ``invalid_grant`` when credentials are valid, or ``invalid_client``
    when they are not.
    """
    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": "startup_ping_invalid_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        body = response.json()
        error = body.get("error", "")

        if error == "invalid_client":
            raise RuntimeError(
                "Google rejected the OAuth client credentials (invalid_client)"
            )
        if error != "invalid_grant":
            raise RuntimeError(
                f"Unexpected Google token endpoint response: {body}"
            )

        logger.info(
            "Google OAuth client credentials check passed",
            extra={"status": "success"},
        )
        return True

    except Exception as e:
        logger.error(
            "Google OAuth client credentials check failed",
            extra={
                "status": "failure",
                "error": str(e),
            },
        )
        raise


@with_retries(retries=5)
def check_google_connections_table(supabase_url: str, service_key: str) -> bool:
    """Verify the google_connections table exists and is readable."""
    try:
        supabase = create_client(supabase_url, service_key)
        supabase.table("google_connections").select("user_id").limit(1).execute()
        logger.info(
            "Google connections table check passed",
            extra={"status": "success"},
        )
        return True

    except Exception as e:
        logger.error(
            "Google connections table check failed",
            extra={
                "status": "failure",
                "error": str(e),
                "hint": (
                    "Apply supabase/migrations/20260712100000_google_connections.sql "
                    "if this table does not exist yet."
                ),
            },
        )
        raise