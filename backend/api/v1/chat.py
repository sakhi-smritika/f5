"""
Chat endpoints backed by the ADK agent.

Conversations are ADK sessions (messages + state) persisted in Supabase Postgres
via ``DatabaseSessionService``. A small ``conversations`` table stores sidebar
metadata (title, timestamps) so the frontend can render a ChatGPT-style history
list directly from Supabase (RLS-scoped), while message content is loaded through
these endpoints from the ADK session's event history.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types
from pydantic import BaseModel

from agent.agent import APP_NAME, get_runner, get_session_service
from agent.tools.context import (
    current_location_label,
    current_now_label,
    current_user_id,
)
from config.auth import AuthenticatedUser, get_current_user
from config.supabase import get_supabase_service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

DEFAULT_TITLE = "New chat"


class CreateConversationBody(BaseModel):
    title: str | None = None


class SendMessageBody(BaseModel):
    text: str
    # The client's current local clock, so the assistant can resolve relative
    # dates ("today", "yesterday"). All optional; falls back to server UTC.
    client_date: str | None = None
    client_time: str | None = None
    client_timezone: str | None = None
    # The client's approximate location as a readable place (city/region/country),
    # reverse-geocoded from browser geolocation when granted.
    client_location: str | None = None


class RenameConversationBody(BaseModel):
    title: str


def _derive_title(text: str) -> str:
    """Build a short conversation title from the first user message."""
    first_line = text.strip().splitlines()[0] if text.strip() else DEFAULT_TITLE
    first_line = first_line.strip()
    if len(first_line) > 40:
        return first_line[:40].rstrip() + "..."
    return first_line or DEFAULT_TITLE


def _get_owned_conversation(conversation_id: str, user_id: str) -> dict:
    """Fetch a conversation row, enforcing ownership. Raises 404 otherwise."""
    client = get_supabase_service_client()
    result = (
        client.table("conversations")
        .select("*")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return rows[0]


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _build_now_label(body: SendMessageBody) -> str:
    """Build a human-readable current-date label from the client's clock.

    Falls back to the server's UTC time if the client didn't send its date.
    """
    if body.client_date:
        try:
            weekday = datetime.strptime(body.client_date, "%Y-%m-%d").strftime("%A")
        except ValueError:
            weekday = ""
        label = f"{weekday}, {body.client_date}".strip(", ")
        if body.client_time:
            label += f" {body.client_time}"
        if body.client_timezone:
            label += f" ({body.client_timezone})"
        return label

    now = datetime.now(timezone.utc)
    return now.strftime("%A, %Y-%m-%d %H:%M (UTC)")


def _build_location_label(body: SendMessageBody) -> str | None:
    """Return the client's readable location, if provided."""
    location = (body.client_location or "").strip()
    return location or None


@router.post("/conversations")
async def create_conversation(
    body: CreateConversationBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Create a new empty conversation (ADK session + metadata row)."""
    conversation_id = str(uuid.uuid4())
    title = (body.title or DEFAULT_TITLE).strip() or DEFAULT_TITLE

    await get_session_service().create_session(
        app_name=APP_NAME, user_id=user.id, session_id=conversation_id
    )

    get_supabase_service_client().table("conversations").insert(
        {"id": conversation_id, "user_id": user.id, "title": title}
    ).execute()

    logger.info("Conversation created", extra={"user_id": user.id})
    return {"id": conversation_id, "title": title}


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Return the message history for a conversation from the ADK session events."""
    _get_owned_conversation(conversation_id, user.id)

    session = await get_session_service().get_session(
        app_name=APP_NAME, user_id=user.id, session_id=conversation_id
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    messages: list[dict] = []
    for event in session.events:
        if not event.content or not event.content.parts:
            continue
        text = "".join(part.text or "" for part in event.content.parts)
        if not text:
            continue
        role = "assistant" if event.content.role == "model" else "user"
        messages.append({"role": role, "text": text})

    return {"messages": messages}


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: SendMessageBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> StreamingResponse:
    """Send a user message and stream the assistant's reply back as SSE."""
    conversation = _get_owned_conversation(conversation_id, user.id)
    runner = get_runner()
    new_message = types.Content(role="user", parts=[types.Part(text=body.text)])

    async def event_stream():
        streamed_any = False
        # Scope tool calls to this user so tools read only their own data.
        token = current_user_id.set(user.id)
        now_token = current_now_label.set(_build_now_label(body))
        location_token = current_location_label.set(_build_location_label(body))
        try:
            async for event in runner.run_async(
                user_id=user.id,
                session_id=conversation_id,
                new_message=new_message,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            ):
                parts = event.content.parts if event.content else None
                text = "".join(part.text or "" for part in parts) if parts else ""
                if not text:
                    continue
                if event.partial:
                    streamed_any = True
                    yield _sse({"delta": text})
                elif event.is_final_response() and not streamed_any:
                    # No partials were emitted (e.g. non-streaming fallback):
                    # send the aggregated text once.
                    yield _sse({"delta": text})

            title = _persist_after_turn(conversation, conversation_id, body.text)
            yield _sse({"done": True, "title": title})
        except Exception:
            logger.exception("Chat stream failed", extra={"user_id": user.id})
            yield _sse({"error": "stream_failed"})
        finally:
            current_user_id.reset(token)
            current_now_label.reset(now_token)
            current_location_label.reset(location_token)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _persist_after_turn(conversation: dict, conversation_id: str, user_text: str) -> str:
    """Update the conversation title (first turn) and bump updated_at."""
    current_title = conversation.get("title")
    new_title = current_title
    if not current_title or current_title == DEFAULT_TITLE:
        new_title = _derive_title(user_text)

    # Any update fires the updated_at trigger, so the sidebar can order by recency.
    get_supabase_service_client().table("conversations").update(
        {"title": new_title}
    ).eq("id", conversation_id).execute()

    return new_title


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(
    conversation_id: str,
    body: RenameConversationBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Rename a conversation's sidebar title."""
    _get_owned_conversation(conversation_id, user.id)

    title = body.title.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Title cannot be empty",
        )

    get_supabase_service_client().table("conversations").update(
        {"title": title}
    ).eq("id", conversation_id).eq("user_id", user.id).execute()

    return {"id": conversation_id, "title": title}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Delete a conversation (ADK session + metadata row)."""
    _get_owned_conversation(conversation_id, user.id)

    try:
        await get_session_service().delete_session(
            app_name=APP_NAME, user_id=user.id, session_id=conversation_id
        )
    except Exception:
        logger.warning(
            "Failed to delete ADK session; removing metadata anyway",
            extra={"user_id": user.id},
        )

    get_supabase_service_client().table("conversations").delete().eq(
        "id", conversation_id
    ).eq("user_id", user.id).execute()

    return {"ok": True}
