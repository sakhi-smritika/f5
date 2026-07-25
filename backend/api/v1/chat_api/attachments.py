import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from agent.chat_agent import APP_NAME, get_session_service
from config.auth import AuthenticatedUser, get_current_user
from config.chat_attachments import (
    attachment_row_to_api,
    build_storage_path,
    create_signed_url,
    delete_from_storage,
    new_attachment_id,
    upload_to_storage,
    validate_upload_file,
)
from config.supabase import get_supabase_service_client

from .access import get_owned_conversation

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/conversations/{conversation_id}/attachments")
async def upload_attachment(
    conversation_id: str,
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Upload a file before sending; returns metadata + a preview URL."""
    get_owned_conversation(conversation_id, user.id)

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
    return {
        **attachment_row_to_api(row, include_url=False),
        "url": create_signed_url(storage_path),
    }


@router.delete("/conversations/{conversation_id}/attachments/{attachment_id}")
async def delete_attachment(
    conversation_id: str,
    attachment_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Remove a not-yet-sent attachment (chip removed before sending)."""
    get_owned_conversation(conversation_id, user.id)

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


async def link_attachments_to_turn(
    conversation_id: str, user_id: str, attachments: list[dict]
) -> None:
    """Stamp the just-persisted user event id onto this turn's attachments."""
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
