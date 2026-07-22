import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from agent.agent import APP_NAME, get_session_service
from config.auth import AuthenticatedUser, get_current_user
from config.supabase import get_supabase_service_client

from .access import get_owned_conversation, get_owned_folder
from .constants import DEFAULT_TITLE
from .schemas import CreateConversationBody, UpdateConversationBody
from .utils import derive_title

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/conversations")
async def create_conversation(
    body: CreateConversationBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Create a new empty conversation (ADK session + metadata row)."""
    conversation_id = str(uuid.uuid4())
    title = (body.title or DEFAULT_TITLE).strip() or DEFAULT_TITLE

    if body.folder_id:
        get_owned_folder(body.folder_id, user.id)

    await get_session_service().create_session(
        app_name=APP_NAME, user_id=user.id, session_id=conversation_id
    )

    row = {"id": conversation_id, "user_id": user.id, "title": title}
    if body.folder_id:
        row["folder_id"] = body.folder_id

    get_supabase_service_client().table("conversations").insert(row).execute()

    logger.info("Conversation created", extra={"user_id": user.id})
    return {"id": conversation_id, "title": title, "folder_id": body.folder_id}


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    body: UpdateConversationBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Rename a conversation and/or move it to a folder."""
    get_owned_conversation(conversation_id, user.id)

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
            get_owned_folder(body.folder_id, user.id)
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
    get_owned_conversation(conversation_id, user.id)
    await delete_conversation_fully(conversation_id, user.id)
    return {"ok": True}


def persist_after_turn(
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
        new_title = derive_title(title_source)

    get_supabase_service_client().table("conversations").update(
        {"title": new_title}
    ).eq("id", conversation_id).execute()

    return new_title


async def delete_conversation_fully(conversation_id: str, user_id: str) -> None:
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

    delete_conversation_attachments(conversation_id, user_id)

    get_supabase_service_client().table("conversations").delete().eq(
        "id", conversation_id
    ).eq("user_id", user_id).execute()


def delete_conversation_attachments(conversation_id: str, user_id: str) -> None:
    """Remove all stored objects for a conversation."""
    from config.chat_attachments import delete_from_storage

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
