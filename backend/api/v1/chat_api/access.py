from fastapi import HTTPException, status

from config.chat_attachments import attachment_row_to_api
from config.supabase import get_supabase_service_client


def get_owned_folder(folder_id: str, user_id: str) -> dict:
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


def get_owned_conversation(conversation_id: str, user_id: str) -> dict:
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


def fetch_pending_attachments(
    conversation_id: str, user_id: str, attachment_ids: list[str]
) -> list[dict]:
    """Fetch unsent attachment rows in the order requested by the client."""
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


def load_attachments_by_event(conversation_id: str, user_id: str) -> dict[str, list[dict]]:
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
