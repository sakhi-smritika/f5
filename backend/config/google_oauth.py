"""
Google Workspace OAuth configuration and helpers.

This module centralises everything needed to run a per-user Google OAuth 2.0
flow (independent of Supabase login) so the agent can act on the user's Calendar
and Tasks:

* Building the ``google_auth_oauthlib`` ``Flow`` from env credentials.
* Signing/verifying the OAuth ``state`` parameter so the callback (which does not
  carry the Supabase bearer token) can be tied back to the right user without a
  server-side session store.
* Encrypting/decrypting refresh tokens at rest with Fernet.

None of these functions touch the database; persistence lives in
``tools.google_tools.google_client``.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from functools import lru_cache

from cryptography.fernet import Fernet
from google_auth_oauthlib.flow import Flow

# Google may return scope aliases (e.g. "email" vs userinfo.email). Relax
# validation so token exchange does not fail on harmless scope differences.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

# Scopes the assistant needs. "openid"/"email" let us capture which Google
# account was connected; calendar + tasks are the actual capabilities.
GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]

# How long a signed OAuth state token stays valid (seconds).
_STATE_TTL_SECONDS = 600


def _get(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise RuntimeError(f"{name} environment variable is required for Google integration")
    return value


def get_redirect_uri() -> str:
    return _get("GOOGLE_OAUTH_REDIRECT_URI")


def get_success_redirect() -> str:
    """Frontend URL to send the user back to after the consent flow."""
    return os.getenv("GOOGLE_OAUTH_SUCCESS_REDIRECT", "http://localhost:5173/settings")


def _client_config() -> dict:
    return {
        "web": {
            "client_id": _get("GOOGLE_CLIENT_ID"),
            "client_secret": _get("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [get_redirect_uri()],
        }
    }


def build_flow(state: str | None = None) -> Flow:
    """Create an OAuth ``Flow`` bound to our client config and redirect URI."""
    flow = Flow.from_client_config(
        _client_config(),
        scopes=GOOGLE_SCOPES,
        state=state,
    )
    flow.redirect_uri = get_redirect_uri()
    return flow


# --- OAuth state signing (stateless CSRF + user binding) -------------------

@lru_cache
def _state_secret() -> bytes:
    # Reuse the Fernet key material as the HMAC secret; it is a high-entropy,
    # backend-only secret already required for this feature.
    return _get("GOOGLE_TOKEN_ENC_KEY").encode()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign_state(
    user_id: str,
    *,
    code_verifier: str | None = None,
    success_redirect: str | None = None,
) -> str:
    """Return a signed, short-lived state token binding the flow to ``user_id``.

    When PKCE is used, pass the ``code_verifier`` generated for the authorize
    step so the callback can complete the token exchange statelessly.

    Optional ``success_redirect`` lets mobile clients return to a custom URL
    scheme after Google finishes (validated in ``resolve_success_redirect``).
    """
    payload = {"uid": user_id, "exp": int(time.time()) + _STATE_TTL_SECONDS}
    if code_verifier:
        payload["cv"] = code_verifier
    if success_redirect:
        payload["sr"] = success_redirect
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(_state_secret(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64url_encode(signature)}"


def verify_state(state: str) -> tuple[str, str | None, str | None]:
    """Verify a state token and return ``(user_id, code_verifier, success_redirect)``.

    Raises ``ValueError`` when the token is invalid or expired.
    """
    try:
        body, provided_sig = state.split(".", 1)
    except ValueError as exc:
        raise ValueError("Malformed state") from exc

    expected_sig = hmac.new(_state_secret(), body.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url_encode(expected_sig), provided_sig):
        raise ValueError("Bad state signature")

    payload = json.loads(_b64url_decode(body))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("State expired")

    user_id = payload.get("uid")
    if not user_id:
        raise ValueError("State missing user")
    return user_id, payload.get("cv"), payload.get("sr")


def resolve_success_redirect(requested: str | None) -> str:
    """Return an allowlisted post-OAuth redirect, falling back to env default."""
    default = get_success_redirect()
    if not requested:
        return default

    requested = requested.strip()
    # Custom URL scheme for the iOS app (ASWebAuthenticationSession).
    if requested.startswith("sakhi-smritika://"):
        return requested.rstrip("/")

    # Same origin as the configured web success redirect.
    default_base = default.rstrip("/")
    if requested.rstrip("/") == default_base or requested.startswith(default_base + "?"):
        return requested.rstrip("/")

    raise ValueError("success_redirect is not allowlisted")


# --- Refresh-token encryption at rest --------------------------------------

@lru_cache
def _fernet() -> Fernet:
    return Fernet(_get("GOOGLE_TOKEN_ENC_KEY").encode())


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(token_enc: str) -> str:
    return _fernet().decrypt(token_enc.encode()).decode()
