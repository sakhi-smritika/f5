"""
Google Workspace integration endpoints.

Per-user OAuth 2.0 flow (independent of Supabase login) so the assistant can
access Calendar and Tasks on behalf of the signed-in user. The callback route
is mounted separately on the app without auth, because Google's redirect does
not carry the Supabase bearer token.
"""

import logging
import secrets
from datetime import timezone
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request

from agent.tools.google_tools.google_client import (
    delete_connection,
    get_connection,
    get_google_credentials,
    get_userinfo_email,
    upsert_connection,
)
from config.auth import AuthenticatedUser, get_current_user
from config.google_oauth import (
    GOOGLE_SCOPES,
    build_flow,
    get_success_redirect,
    sign_state,
    verify_state,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])

# Mounted on the app directly (no bearer auth) — see ``app.py``.
callback_router = APIRouter(tags=["integrations"])


def _redirect_with_status(*, success: bool, message: str = "") -> RedirectResponse:
    params: dict[str, str] = {"google": "connected" if success else "error"}
    if message:
        params["message"] = message
    base = get_success_redirect().rstrip("/")
    return RedirectResponse(url=f"{base}?{urlencode(params)}", status_code=302)


@router.get("/google/authorize")
def google_authorize(user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """Return the Google consent URL for the signed-in user to open."""
    code_verifier = secrets.token_urlsafe(64)
    state = sign_state(user.id, code_verifier=code_verifier)
    flow = build_flow(state=state)
    flow.code_verifier = code_verifier
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return {"url": auth_url}


@callback_router.get("/api/v1/integrations/google/callback")
def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """OAuth redirect target. Exchanges the code and stores encrypted tokens."""
    if error:
        logger.warning("Google OAuth denied", extra={"error": error})
        return _redirect_with_status(success=False, message=error)

    if not code or not state:
        return _redirect_with_status(success=False, message="Missing code or state")

    try:
        user_id, code_verifier = verify_state(state)
    except ValueError as exc:
        logger.warning("Invalid Google OAuth state", extra={"detail": str(exc)})
        return _redirect_with_status(success=False, message="Invalid or expired state")

    try:
        flow = build_flow(state=state)
        if code_verifier:
            flow.code_verifier = code_verifier
        flow.fetch_token(code=code)
        creds = flow.credentials
    except Exception as exc:
        logger.error(
            "Google token exchange failed: %s",
            exc,
            extra={
                "user_id": user_id,
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )
        return _redirect_with_status(
            success=False,
            message=f"Token exchange failed: {exc}",
        )

    if not creds.refresh_token:
        logger.error(
            "Google OAuth completed without refresh token",
            extra={"user_id": user_id},
        )
        return _redirect_with_status(
            success=False,
            message="No refresh token received; try disconnecting and reconnecting",
        )

    expiry = creds.expiry
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    google_email = get_userinfo_email(creds)
    upsert_connection(
        user_id,
        refresh_token=creds.refresh_token,
        access_token=creds.token,
        token_expiry=expiry,
        scopes=list(creds.scopes or GOOGLE_SCOPES),
        google_email=google_email,
    )
    logger.info("Google connected", extra={"user_id": user_id, "google_email": google_email})
    return _redirect_with_status(success=True)


@router.get("/google/status")
def google_status(user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """Return whether the user has connected Google and which account."""
    row = get_connection(user.id)
    if not row:
        return {"connected": False, "google_email": None}
    return {
        "connected": True,
        "google_email": row.get("google_email"),
        "connected_at": row.get("created_at"),
    }


@router.delete("/google", status_code=status.HTTP_204_NO_CONTENT)
def google_disconnect(user: AuthenticatedUser = Depends(get_current_user)) -> None:
    """Revoke stored tokens and remove the user's Google connection."""
    creds = get_google_credentials(user.id)
    if creds and creds.token:
        try:
            body = urlencode({"token": creds.token}).encode()
            urlopen(
                UrlRequest(
                    "https://oauth2.googleapis.com/revoke",
                    data=body,
                    method="POST",
                ),
                timeout=10,
            )
        except Exception:
            logger.warning(
                "Failed to revoke Google access token",
                extra={"user_id": user.id},
            )

    if creds and creds.refresh_token:
        try:
            creds.revoke(Request())
        except Exception:
            logger.warning(
                "Failed to revoke Google refresh token",
                extra={"user_id": user.id},
            )

    delete_connection(user.id)
    logger.info("Google disconnected", extra={"user_id": user.id})
