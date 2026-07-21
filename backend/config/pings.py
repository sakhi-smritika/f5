# pylint: disable=broad-exception-caught
"""
Module Exposes a function to test if all API and SECURE KEYs are work
All Ping Functions should be inside the class 'Pings' and should start with 'ping_'
These 'ping_' functions should not take any arguments and should return True if the ping is successful, False otherwise.
"""

import os
import functools
import logging
import time

import litellm
import requests
from cryptography.fernet import Fernet, InvalidToken
from google_auth_oauthlib.flow import Flow
from supabase import create_client

from config.google_oauth import GOOGLE_SCOPES

DEFAULT_LITELLM_PING_PROMPT = "Reply with a short confirmation that the API key is working."

logger = logging.getLogger(__name__)

class Pings:

    @staticmethod
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

    @staticmethod
    def _ping_litellm_api_key(*, env_var: str, model: str, provider_name: str) -> bool:
        """Ping a LiteLLM-backed provider using the configured API key."""
        api_key = os.getenv(env_var)
        if not api_key:
            logger.warning(
                f"{provider_name} API key is not set",
                extra={
                    "status": "failure",
                    "error": f"{env_var} environment variable is missing",
                },
            )
            return False

        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": DEFAULT_LITELLM_PING_PROMPT}],
                api_key=api_key,
            )
            response_preview = (
                response.choices[0].message.content[:10]
                if response.choices and response.choices[0].message.content
                else None
            )
            logger.info(
                f"{provider_name} API key check passed",
                extra={
                    "status": "success",
                    "response_preview": response_preview,
                },
            )
            return True

        except Exception as e:
            logger.error(
                f"{provider_name} API key check failed",
                extra={
                    "status": "failure",
                    "error": str(e),
                },
            )
            return False

    
    @staticmethod
    @with_retries(retries=5)
    def ping_gemini_api_key():
        """To Check if Gemini Key works"""
        return Pings._ping_litellm_api_key(
            env_var="GEMINI_API_KEY",
            model="gemini/gemini-2.5-flash",
            provider_name="Gemini",
        )


    @staticmethod
    @with_retries(retries=5)
    def ping_openai_api_key() -> bool:
        """To Check if OPENAI API KEY works"""
        return Pings._ping_litellm_api_key(
            env_var="OPENAI_API_KEY",
            model="openai/gpt-4.1-mini",
            provider_name="OpenAI",
        )


    @staticmethod
    @with_retries(retries=5)
    def ping_anthropic_api_key() -> bool:
        """To Check if Anthropic API KEY works"""
        return Pings._ping_litellm_api_key(
            env_var="ANTHROPIC_API_KEY",
            model="anthropic/claude-3-5-sonnet-latest",
            provider_name="Anthropic",
        )


    @staticmethod
    @with_retries(retries=5)
    def ping_supabase_connection() -> bool:
        """To check if SUPABASE_URL and SUPABASE_ANON_KEY works"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_anon_key:
            logger.warning(
                "Supabase connection details are not set",
                extra={
                    "status": "failure",
                    "error": "SUPABASE_URL or SUPABASE_ANON_KEY environment variables are missing",
                },
            )
            return False

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
            return False


    @staticmethod
    @with_retries(retries=5)
    def ping_supabase_secret_key() -> bool:
        """To check if SUPABASE_SECRET_KEY works"""
        supabase_url = os.getenv("SUPABASE_URL")
        secret_key = os.getenv("SUPABASE_SECRET_KEY")

        if not supabase_url or not secret_key:
            logger.warning(
                "Supabase secret key details are not set",
                extra={
                    "status": "failure",
                    "error": "SUPABASE_URL or SUPABASE_SECRET_KEY environment variables are missing",
                },
            )
            return False

        try:
            supabase = create_client(supabase_url, secret_key)

            # Secret key must bypass RLS
            # This query should succeed even if RLS is enabled
            supabase.table("users").select("id").limit(1).execute()
            logger.info(
                "Supabase secret key check passed",
                extra={
                    "status": "success",
                },
            )
            return True

        except Exception as e:
            logger.error(
                "Supabase secret key check failed",
                extra={
                    "status": "failure",
                    "error": str(e),
                },
            )
            raise


    @staticmethod
    @with_retries(retries=5)
    def ping_google_token_enc_key() -> bool:
        """Verify GOOGLE_TOKEN_ENC_KEY is a valid Fernet key and can round-trip."""
        token_enc_key = os.getenv("GOOGLE_TOKEN_ENC_KEY")
        if not token_enc_key:
            logger.warning(
                "Google token encryption key is not set",
                extra={
                    "status": "failure",
                    "error": "GOOGLE_TOKEN_ENC_KEY environment variable is missing",
                },
            )
            return False
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


    @staticmethod
    @with_retries(retries=5)
    def ping_google_oauth_flow() -> bool:
        """Verify OAuth client config can build a consent URL."""
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        if not client_id or not client_secret or not redirect_uri:
            logger.warning(
                "Google OAuth client details are not set",
                extra={
                    "status": "failure",
                    "error": "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, or GOOGLE_REDIRECT_URI environment variables are missing",
                },
            )
            return False
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


    @staticmethod
    @with_retries(retries=5)
    def ping_google_oauth_client() -> bool:
        """Probe Google's token endpoint to confirm client id/secret are accepted.

        We intentionally exchange a bogus authorization code. Google should answer
        with ``invalid_grant`` when credentials are valid, or ``invalid_client``
        when they are not.
        """
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        if not client_id or not client_secret or not redirect_uri:
            logger.warning(
                "Google OAuth client details are not set",
                extra={
                    "status": "failure",
                    "error": "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, or GOOGLE_REDIRECT_URI environment variables are missing",
                },
            )
            return False
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


    @staticmethod
    @with_retries(retries=5)
    def ping_google_connections_table() -> bool:
        """Verify the google_connections table exists and is readable."""
        supabase_url = os.getenv("SUPABASE_URL")
        service_key = os.getenv("SUPABASE_SERVICE_KEY")
        if not supabase_url or not service_key:
            logger.warning(
                "Supabase service key details are not set",
                extra={
                    "status": "failure",
                    "error": "SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables are missing",
                },
            )
            return False
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