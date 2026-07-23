"""Discussion (comment thread) endpoint for a knowledge bit.

A discussion reuses the normal chat machinery: it is a ``conversations`` row
plus an ADK session, linked to its bit via ``kbit_id``. The bit is injected into
the agent's system prompt at message time (see ``agent._instruction_provider``),
so it is never stored as a chat message. Threads are created lazily — only when
the user actually opens the comment section — so generating bits never spawns
empty conversations.

Message history and streaming reuse the chat endpoints
(``GET/POST /chat/conversations/{id}/messages``); this module only gets or
creates the conversation for a bit.
"""

import logging
import uuid

from fastapi import APIRouter, Depends

from agent.agent import APP_NAME, get_session_service
from config.auth import AuthenticatedUser, get_current_user
from config.supabase import get_supabase_service_client

from .access import get_owned_kbit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kbits", tags=["kbits"])

_FALLBACK_TITLE = "Knowledge bit"


@router.post("/{kbit_id}/discussion")
async def ensure_discussion(
    kbit_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Get or lazily create the discussion conversation for a knowledge bit."""
    bit = get_owned_kbit(kbit_id, user.id)

    client = get_supabase_service_client()
    existing = (
        client.table("conversations")
        .select("id")
        .eq("kbit_id", kbit_id)
        .eq("user_id", user.id)
        .limit(1)
        .execute()
    )
    rows = existing.data or []
    if rows:
        return {"conversation_id": rows[0]["id"], "created": False}

    conversation_id = str(uuid.uuid4())
    await get_session_service().create_session(
        app_name=APP_NAME, user_id=user.id, session_id=conversation_id
    )

    title = (bit.get("title") or "").strip() or _FALLBACK_TITLE
    client.table("conversations").insert(
        {
            "id": conversation_id,
            "user_id": user.id,
            "title": title,
            "kbit_id": kbit_id,
        }
    ).execute()

    logger.info("Kbit discussion created", extra={"user_id": user.id})
    return {"conversation_id": conversation_id, "created": True}
