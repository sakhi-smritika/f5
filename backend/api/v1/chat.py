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

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types
from pydantic import BaseModel

from agent.agent import APP_NAME, get_runner, get_session_service
from agent.attachment_parts import build_user_message_parts, is_attachment_text
from agent.tools.context import (
    current_location_label,
    current_now_label,
    current_user_id,
)
from config.auth import AuthenticatedUser, get_current_user
from config.chat_attachments import (
    attachment_row_to_api,
    build_storage_path,
    create_signed_url,
    delete_from_storage,
    download_from_storage,
    new_attachment_id,
    upload_to_storage,
    validate_upload_file,
)
from config.llm_keys import MissingApiKeyError, get_api_key_for_model
from config.models import resolve_model
from config.supabase import get_supabase_service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

DEFAULT_TITLE = "New chat"


class CreateConversationBody(BaseModel):
    title: str | None = None
    folder_id: str | None = None


class UpdateConversationBody(BaseModel):
    title: str | None = None
    folder_id: str | None = None


class SendMessageBody(BaseModel):
    text: str
    attachment_ids: list[str] = []
    model: str | None = None
    # The client's current local clock, so the assistant can resolve relative
    # dates ("today", "yesterday"). All optional; falls back to server UTC.
    client_date: str | None = None
    client_time: str | None = None
    client_timezone: str | None = None
    # The client's approximate location as a readable place (city/region/country),
    # reverse-geocoded from browser geolocation when granted.
    client_location: str | None = None


def _derive_title(text: str) -> str:
    """Build a short conversation title from the first user message."""
    first_line = text.strip().splitlines()[0] if text.strip() else DEFAULT_TITLE
    first_line = first_line.strip()
    if len(first_line) > 40:
        return first_line[:40].rstrip() + "..."
    return first_line or DEFAULT_TITLE


def _get_owned_folder(folder_id: str, user_id: str) -> dict:
    """Fetch a folder row, enforcing ownership. Raises 404 otherwise."""
    client = get_supabase_service_client()
    result = (
        client.table("chat_folder")
        .select("*")
        .eq("id", folder_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )
    return rows[0]


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


def _fetch_pending_attachments(
    conversation_id: str, user_id: str, attachment_ids: list[str]
) -> list[dict]:
    """Fetch attachment rows that belong to the user/conversation and are unsent.

    Preserves the order of ``attachment_ids`` so files appear as the user added
    them. Raises 404 if any requested id is missing, foreign, or already linked.
    """
    if not attachment_ids:
        return []

    client = get_supabase_service_client()
    result = (
        client.table("chat_attachments")
        .select("*")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user_id)
        .is_("adk_event_id", "null")
        .in_("id", attachment_ids)
        .execute()
    )
    rows = {row["id"]: row for row in (result.data or [])}
    ordered: list[dict] = []
    for attachment_id in attachment_ids:
        row = rows.get(attachment_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attachment not found or already sent: {attachment_id}",
            )
        ordered.append(row)
    return ordered


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

    if body.folder_id:
        _get_owned_folder(body.folder_id, user.id)

    await get_session_service().create_session(
        app_name=APP_NAME, user_id=user.id, session_id=conversation_id
    )

    row = {"id": conversation_id, "user_id": user.id, "title": title}
    if body.folder_id:
        row["folder_id"] = body.folder_id

    get_supabase_service_client().table("conversations").insert(row).execute()

    logger.info("Conversation created", extra={"user_id": user.id})
    return {"id": conversation_id, "title": title, "folder_id": body.folder_id}


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

    attachments_by_event = _load_attachments_by_event(conversation_id, user.id)

    messages: list[dict] = []
    for event in session.events:
        if not event.content or not event.content.parts:
            continue
        # Skip text injected from file attachments; the attachment card already
        # represents the file, so the extracted content isn't shown in the bubble.
        text = "".join(
            part.text or ""
            for part in event.content.parts
            if not is_attachment_text(part.text)
        )
        role = "assistant" if event.content.role == "model" else "user"
        attachments = attachments_by_event.get(event.id, []) if role == "user" else []
        if not text and not attachments:
            continue
        messages.append(
            {
                "role": role,
                "text": text,
                "event_id": event.id,
                "attachments": attachments,
            }
        )

    return {"messages": messages}


def _load_attachments_by_event(conversation_id: str, user_id: str) -> dict[str, list[dict]]:
    """Group a conversation's sent attachments by their linked ADK event id."""
    client = get_supabase_service_client()
    result = (
        client.table("chat_attachments")
        .select("*")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user_id)
        .not_.is_("adk_event_id", "null")
        .order("created_at")
        .execute()
    )
    grouped: dict[str, list[dict]] = {}
    for row in result.data or []:
        grouped.setdefault(row["adk_event_id"], []).append(
            attachment_row_to_api(row)
        )
    return grouped


@router.post("/conversations/{conversation_id}/attachments")
async def upload_attachment(
    conversation_id: str,
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Upload a file before sending; returns metadata + a preview URL.

    The row is created unlinked (``adk_event_id`` is null) and is attached to a
    message only when the user actually sends. Unsent rows can be deleted or
    cleaned up later.
    """
    _get_owned_conversation(conversation_id, user.id)

    data = await file.read()
    mime_type = validate_upload_file(file, data)
    filename = (file.filename or "").strip() or "upload"

    attachment_id = new_attachment_id()
    storage_path = build_storage_path(
        user.id, conversation_id, attachment_id, filename, mime_type
    )
    upload_to_storage(storage_path, data, mime_type)

    row = {
        "id": attachment_id,
        "conversation_id": conversation_id,
        "user_id": user.id,
        "storage_path": storage_path,
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": len(data),
    }
    try:
        get_supabase_service_client().table("chat_attachments").insert(row).execute()
    except Exception:
        delete_from_storage(storage_path)
        raise

    logger.info("Attachment uploaded", extra={"user_id": user.id})
    return {**attachment_row_to_api(row, include_url=False), "url": create_signed_url(storage_path)}


@router.delete("/conversations/{conversation_id}/attachments/{attachment_id}")
async def delete_attachment(
    conversation_id: str,
    attachment_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Remove a not-yet-sent attachment (chip removed before sending)."""
    _get_owned_conversation(conversation_id, user.id)

    client = get_supabase_service_client()
    result = (
        client.table("chat_attachments")
        .select("*")
        .eq("id", attachment_id)
        .eq("conversation_id", conversation_id)
        .eq("user_id", user.id)
        .is_("adk_event_id", "null")
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found or already sent",
        )

    delete_from_storage(rows[0]["storage_path"])
    client.table("chat_attachments").delete().eq("id", attachment_id).execute()
    return {"ok": True}


def _stream_error_message(exc: Exception, model_id: str) -> str:
    """Turn an LLM exception into a short client-facing message."""
    message = str(exc)
    if "not_found_error" in message or "NotFoundError" in type(exc).__name__:
        return f"Model not available: {model_id}. Check CHAT_MODELS uses a valid model id for your API key."
    if "authentication" in message.lower() or "api_key" in message.lower():
        return "Invalid or missing API key for the selected model's provider."
    trimmed = message.strip()
    if trimmed and len(trimmed) <= 200:
        return trimmed
    if trimmed:
        return trimmed[:200] + "..."
    return "The assistant failed to respond."


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: SendMessageBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> StreamingResponse:
    """Send a user message and stream the assistant's reply back as SSE."""
    conversation = _get_owned_conversation(conversation_id, user.id)
    try:
        model_id = resolve_model(body.model)
        get_api_key_for_model(model_id)
    except MissingApiKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    attachments = _fetch_pending_attachments(
        conversation_id, user.id, body.attachment_ids
    )
    attachment_bytes = [
        download_from_storage(row["storage_path"]) for row in attachments
    ]
    parts = build_user_message_parts(
        body.text, attachments, attachment_bytes, model_id=model_id
    )

    runner = get_runner(model_id)
    new_message = types.Content(role="user", parts=parts)

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

            if attachments:
                await _link_attachments_to_turn(
                    conversation_id, user.id, attachments
                )
            title = _persist_after_turn(
                conversation, conversation_id, body.text, attachments
            )
            yield _sse({"done": True, "title": title})
        except Exception as exc:
            logger.exception(
                "Chat stream failed",
                extra={"user_id": user.id, "model_id": model_id},
            )
            yield _sse({"error": _stream_error_message(exc, model_id)})
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


async def _link_attachments_to_turn(
    conversation_id: str, user_id: str, attachments: list[dict]
) -> None:
    """Stamp the just-persisted user event id onto this turn's attachments.

    ADK appends one user event per turn; the last user event in the session is
    the message we just sent, so we link the attachments to it.
    """
    session = await get_session_service().get_session(
        app_name=APP_NAME, user_id=user_id, session_id=conversation_id
    )
    event_id = None
    for event in reversed(session.events if session else []):
        if event.content and event.content.role == "user":
            event_id = event.id
            break
    if not event_id:
        logger.warning(
            "Could not find user event to link attachments",
            extra={"user_id": user_id},
        )
        return

    client = get_supabase_service_client()
    client.table("chat_attachments").update({"adk_event_id": event_id}).in_(
        "id", [row["id"] for row in attachments]
    ).execute()


def _persist_after_turn(
    conversation: dict,
    conversation_id: str,
    user_text: str,
    attachments: list[dict] | None = None,
) -> str:
    """Update the conversation title (first turn) and bump updated_at."""
    current_title = conversation.get("title")
    new_title = current_title
    if not current_title or current_title == DEFAULT_TITLE:
        title_source = user_text.strip()
        if not title_source and attachments:
            title_source = attachments[0]["filename"]
        new_title = _derive_title(title_source)

    # Any update fires the updated_at trigger, so the sidebar can order by recency.
    get_supabase_service_client().table("conversations").update(
        {"title": new_title}
    ).eq("id", conversation_id).execute()

    return new_title


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    body: UpdateConversationBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Rename a conversation and/or move it to a folder."""
    _get_owned_conversation(conversation_id, user.id)

    updates: dict = {}
    if body.title is not None:
        title = body.title.strip()
        if not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Title cannot be empty",
            )
        updates["title"] = title

    if "folder_id" in body.model_fields_set:
        if body.folder_id:
            _get_owned_folder(body.folder_id, user.id)
        updates["folder_id"] = body.folder_id

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No updates provided",
        )

    get_supabase_service_client().table("conversations").update(updates).eq(
        "id", conversation_id
    ).eq("user_id", user.id).execute()

    result = {"id": conversation_id}
    if "title" in updates:
        result["title"] = updates["title"]
    if "folder_id" in updates:
        result["folder_id"] = updates["folder_id"]
    return result


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Delete a conversation (ADK session + metadata row)."""
    _get_owned_conversation(conversation_id, user.id)
    await _delete_conversation_fully(conversation_id, user.id)
    return {"ok": True}


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Delete a folder and all conversations inside it."""
    _get_owned_folder(folder_id, user.id)

    client = get_supabase_service_client()
    result = (
        client.table("conversations")
        .select("id")
        .eq("folder_id", folder_id)
        .eq("user_id", user.id)
        .execute()
    )
    for row in result.data or []:
        await _delete_conversation_fully(row["id"], user.id)

    client.table("chat_folder").delete().eq("id", folder_id).eq(
        "user_id", user.id
    ).execute()

    return {"ok": True}


async def _delete_conversation_fully(conversation_id: str, user_id: str) -> None:
    """Remove ADK session, attachments, and metadata for one conversation."""
    try:
        await get_session_service().delete_session(
            app_name=APP_NAME, user_id=user_id, session_id=conversation_id
        )
    except Exception:
        logger.warning(
            "Failed to delete ADK session; removing metadata anyway",
            extra={"user_id": user_id},
        )

    _delete_conversation_attachments(conversation_id, user_id)

    get_supabase_service_client().table("conversations").delete().eq(
        "id", conversation_id
    ).eq("user_id", user_id).execute()


def _delete_conversation_attachments(conversation_id: str, user_id: str) -> None:
    """Remove all stored objects for a conversation. Rows cascade with the row."""
    client = get_supabase_service_client()
    result = (
        client.table("chat_attachments")
        .select("storage_path")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user_id)
        .execute()
    )
    paths = [row["storage_path"] for row in (result.data or [])]
    if not paths:
        return
    try:
        delete_from_storage(*paths)
    except Exception:
        logger.warning(
            "Failed to delete some attachment objects",
            extra={"user_id": user_id},
        )
