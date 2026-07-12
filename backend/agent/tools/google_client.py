"""
Per-user Google API client access.

Turns a Supabase ``user_id`` into authorized Google Calendar / Tasks service
clients by loading that user's stored (encrypted) refresh token from
``public.google_connections``, refreshing the access token when needed, and
persisting the refreshed token back. All database access uses the service-role
client; refresh tokens never leave the backend.
"""

import logging
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.google_oauth import (
    GOOGLE_SCOPES,
    decrypt_token,
    encrypt_token,
)
from config.supabase import get_supabase_service_client

logger = logging.getLogger(__name__)

_TOKEN_URI = "https://oauth2.googleapis.com/token"
_TABLE = "google_connections"


def _client_id_secret() -> tuple[str, str]:
    # Imported lazily so importing this module never requires the env vars.
    import os

    return os.getenv("GOOGLE_CLIENT_ID", ""), os.getenv("GOOGLE_CLIENT_SECRET", "")


def get_connection(user_id: str) -> dict | None:
    """Return the raw google_connections row for a user, or ``None``."""
    result = (
        get_supabase_service_client()
        .table(_TABLE)
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def upsert_connection(
    user_id: str,
    *,
    refresh_token: str,
    access_token: str | None,
    token_expiry: datetime | None,
    scopes: list[str],
    google_email: str | None,
) -> None:
    """Create or update a user's Google connection with an encrypted refresh token."""
    payload = {
        "user_id": user_id,
        "refresh_token_enc": encrypt_token(refresh_token),
        "access_token": access_token,
        "token_expiry": token_expiry.isoformat() if token_expiry else None,
        "scopes": scopes,
        "google_email": google_email,
    }
    get_supabase_service_client().table(_TABLE).upsert(
        payload, on_conflict="user_id"
    ).execute()


def delete_connection(user_id: str) -> None:
    get_supabase_service_client().table(_TABLE).delete().eq("user_id", user_id).execute()


def _persist_refreshed(user_id: str, creds: Credentials) -> None:
    """Store a freshly refreshed access token + expiry (refresh token unchanged)."""
    expiry = creds.expiry
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    get_supabase_service_client().table(_TABLE).update(
        {
            "access_token": creds.token,
            "token_expiry": expiry.isoformat() if expiry else None,
        }
    ).eq("user_id", user_id).execute()


def get_google_credentials(user_id: str) -> Credentials | None:
    """Return valid Google credentials for ``user_id`` or ``None`` if not connected."""
    row = get_connection(user_id)
    if not row:
        return None

    client_id, client_secret = _client_id_secret()
    try:
        refresh_token = decrypt_token(row["refresh_token_enc"])
    except Exception:
        logger.exception("Failed to decrypt Google refresh token", extra={"user_id": user_id})
        return None

    creds = Credentials(
        token=row.get("access_token"),
        refresh_token=refresh_token,
        token_uri=_TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=row.get("scopes") or GOOGLE_SCOPES,
    )

    if not creds.valid:
        try:
            creds.refresh(Request())
            _persist_refreshed(user_id, creds)
        except Exception:
            logger.exception("Failed to refresh Google token", extra={"user_id": user_id})
            return None

    return creds


def get_calendar_service(user_id: str):
    """Return an authorized Calendar v3 service, or ``None`` if not connected."""
    creds = get_google_credentials(user_id)
    if creds is None:
        return None
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_tasks_service(user_id: str):
    """Return an authorized Tasks v1 service, or ``None`` if not connected."""
    creds = get_google_credentials(user_id)
    if creds is None:
        return None
    return build("tasks", "v1", credentials=creds, cache_discovery=False)


def get_userinfo_email(creds: Credentials) -> str | None:
    """Best-effort fetch of the connected Google account's email address."""
    try:
        service = build("oauth2", "v2", credentials=creds, cache_discovery=False)
        info = service.userinfo().get().execute()
        return info.get("email")
    except Exception:
        logger.warning("Failed to fetch Google userinfo email")
        return None
