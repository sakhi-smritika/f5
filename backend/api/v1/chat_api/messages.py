import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types

from agent.agent import APP_NAME, get_runner, get_session_service
from agent.attachment_parts import build_user_message_parts, is_attachment_text
from agent.tools.context import (
    current_location_label,
    current_now_label,
    current_user_id,
)
from config.auth import AuthenticatedUser, get_current_user
from config.chat_attachments import download_from_storage
from config.llm_keys import MissingApiKeyError, get_api_key_for_model
from config.models import resolve_model

from .access import fetch_pending_attachments, get_owned_conversation, load_attachments_by_event
from .attachments import link_attachments_to_turn
from .conversations import persist_after_turn
from .schemas import SendMessageBody
from .utils import build_location_label, build_now_label, sse, stream_error_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Return the message history for a conversation from the ADK session events."""
    get_owned_conversation(conversation_id, user.id)

    session = await get_session_service().get_session(
        app_name=APP_NAME, user_id=user.id, session_id=conversation_id
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    attachments_by_event = load_attachments_by_event(conversation_id, user.id)

    messages: list[dict] = []
    for event in session.events:
        if not event.content or not event.content.parts:
            continue
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


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: SendMessageBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> StreamingResponse:
    """Send a user message and stream the assistant's reply back as SSE."""
    conversation = get_owned_conversation(conversation_id, user.id)
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

    attachments = fetch_pending_attachments(
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
        token = current_user_id.set(user.id)
        now_token = current_now_label.set(build_now_label(body))
        location_token = current_location_label.set(build_location_label(body))
        try:
            async for event in runner.run_async(
                user_id=user.id,
                session_id=conversation_id,
                new_message=new_message,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            ):
                event_parts = event.content.parts if event.content else None
                text = "".join(part.text or "" for part in event_parts) if event_parts else ""
                if not text:
                    continue
                if event.partial:
                    streamed_any = True
                    yield sse({"delta": text})
                elif event.is_final_response() and not streamed_any:
                    yield sse({"delta": text})

            if attachments:
                await link_attachments_to_turn(
                    conversation_id, user.id, attachments
                )
            title = persist_after_turn(
                conversation, conversation_id, body.text, attachments
            )
            yield sse({"done": True, "title": title})
        except Exception as exc:
            logger.exception(
                "Chat stream failed",
                extra={"user_id": user.id, "model_id": model_id},
            )
            yield sse({"error": stream_error_message(exc, model_id)})
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
