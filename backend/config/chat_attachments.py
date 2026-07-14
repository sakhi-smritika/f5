"""Supabase Storage helpers for chat file attachments."""

from __future__ import annotations

import mimetypes
import os
import uuid
from typing import Any

from fastapi import HTTPException, UploadFile, status

from config.supabase import get_supabase_service_client

CHAT_ATTACHMENTS_BUCKET = "chat-attachments"
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
SIGNED_URL_EXPIRY_SECONDS = 3600

# MIME types we accept natively or can normalize to text for the LLM.
ALLOWED_MIME_PREFIXES = ("image/", "text/")
ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "application/json",
        "application/javascript",
        "application/xml",
        "application/x-yaml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
)


def _guess_extension(filename: str, mime_type: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext:
        return ext
    guessed = mimetypes.guess_extension(mime_type.split(";", 1)[0].strip())
    return guessed or ""


def validate_upload_file(file: UploadFile, data: bytes) -> str:
    """Return normalized MIME type or raise HTTP 422."""
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empty file",
        )
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB limit",
        )

    filename = (file.filename or "").strip() or "upload"
    declared = (file.content_type or "").split(";", 1)[0].strip().lower()
    guessed, _ = mimetypes.guess_type(filename)
    mime_type = declared or (guessed or "application/octet-stream").lower()

    if mime_type.startswith(ALLOWED_MIME_PREFIXES) or mime_type in ALLOWED_MIME_TYPES:
        return mime_type

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unsupported file type: {mime_type}",
    )


def build_storage_path(user_id: str, conversation_id: str, attachment_id: str, filename: str, mime_type: str) -> str:
    ext = _guess_extension(filename, mime_type)
    return f"{user_id}/{conversation_id}/{attachment_id}{ext}"


def upload_to_storage(storage_path: str, data: bytes, mime_type: str) -> None:
    client = get_supabase_service_client()
    client.storage.from_(CHAT_ATTACHMENTS_BUCKET).upload(
        storage_path,
        data,
        {"content-type": mime_type, "upsert": "false"},
    )


def download_from_storage(storage_path: str) -> bytes:
    client = get_supabase_service_client()
    return client.storage.from_(CHAT_ATTACHMENTS_BUCKET).download(storage_path)


def delete_from_storage(*storage_paths: str) -> None:
    if not storage_paths:
        return
    client = get_supabase_service_client()
    client.storage.from_(CHAT_ATTACHMENTS_BUCKET).remove(list(storage_paths))


def create_signed_url(storage_path: str) -> str:
    client = get_supabase_service_client()
    result = client.storage.from_(CHAT_ATTACHMENTS_BUCKET).create_signed_url(
        storage_path,
        SIGNED_URL_EXPIRY_SECONDS,
    )
    signed = result.get("signedURL") or result.get("signedUrl")
    if not signed:
        raise RuntimeError("Failed to create signed URL for attachment")
    return signed


def new_attachment_id() -> str:
    return str(uuid.uuid4())


def attachment_row_to_api(row: dict[str, Any], *, include_url: bool = True) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "filename": row["filename"],
        "mime_type": row["mime_type"],
        "size_bytes": row["size_bytes"],
    }
    if include_url:
        payload["url"] = create_signed_url(row["storage_path"])
    return payload
