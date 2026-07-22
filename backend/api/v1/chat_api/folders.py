from fastapi import APIRouter, Depends

from config.auth import AuthenticatedUser, get_current_user
from config.supabase import get_supabase_service_client

from .access import get_owned_folder
from .conversations import delete_conversation_fully

router = APIRouter()


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Delete a folder and all conversations inside it."""
    get_owned_folder(folder_id, user.id)

    client = get_supabase_service_client()
    result = (
        client.table("conversations")
        .select("id")
        .eq("folder_id", folder_id)
        .eq("user_id", user.id)
        .execute()
    )
    for row in result.data or []:
        await delete_conversation_fully(row["id"], user.id)

    client.table("chat_folder").delete().eq("id", folder_id).eq(
        "user_id", user.id
    ).execute()

    return {"ok": True}
