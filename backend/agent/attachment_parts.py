"""Build ADK / GenAI Content parts from chat attachment bytes."""

from __future__ import annotations

import io
from typing import Any

from fastapi import HTTPException, status
from google.genai import types

from config.llm_keys import get_model_provider

MAX_TEXT_EXTRACT_CHARS = 120_000

# Prefix stamped onto text parts that carry extracted file content (PDF/text).
# The model reads these, but ``get_messages`` strips them so the extracted text
# is never shown in the user's chat bubble (the attachment card represents the
# file instead). Uses a zero-width sentinel that won't occur in typed text.
ATTACHMENT_TEXT_MARKER = "\u200b\u2063attachment\u2063\u200b"


def is_attachment_text(text: str | None) -> bool:
    """True if a part's text was injected from a file attachment."""
    return bool(text) and text.startswith(ATTACHMENT_TEXT_MARKER)


def _decode_text(data: bytes, filename: str) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not decode {filename} as text",
        )
    if len(text) > MAX_TEXT_EXTRACT_CHARS:
        text = text[:MAX_TEXT_EXTRACT_CHARS] + "\n… [truncated]"
    return text


def _extract_pdf_text(data: bytes, filename: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF support is not available on the server",
        ) from exc

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n\n".join(pages).strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not extract text from PDF: {filename}",
        )
    if len(text) > MAX_TEXT_EXTRACT_CHARS:
        text = text[:MAX_TEXT_EXTRACT_CHARS] + "\n… [truncated]"
    return text


def build_parts_for_attachment(
    attachment: dict[str, Any],
    data: bytes,
    *,
    model_id: str,
) -> list[types.Part]:
    """Turn one attachment into one or more GenAI parts for the user message."""
    mime_type = attachment["mime_type"]
    filename = attachment["filename"]
    provider = get_model_provider(model_id)
    parts: list[types.Part] = []

    if mime_type.startswith("image/"):
        parts.append(
            types.Part(
                inline_data=types.Blob(mime_type=mime_type, data=data),
            )
        )
        return parts

    if mime_type == "application/pdf":
        if provider == "gemini":
            parts.append(
                types.Part(
                    inline_data=types.Blob(mime_type=mime_type, data=data),
                )
            )
            return parts
        text = _extract_pdf_text(data, filename)
        parts.append(
            types.Part(
                text=f"{ATTACHMENT_TEXT_MARKER}[Attached PDF: {filename}]\n\n{text}"
            ),
        )
        return parts

    if mime_type.startswith("text/") or mime_type in {
        "application/json",
        "application/javascript",
        "application/xml",
        "application/x-yaml",
    }:
        text = _decode_text(data, filename)
        parts.append(
            types.Part(
                text=f"{ATTACHMENT_TEXT_MARKER}[Attached file: {filename}]\n\n{text}"
            ),
        )
        return parts

    # Last resort for odd types: try plain-text decode.
    try:
        text = _decode_text(data, filename)
    except HTTPException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type for {filename}: {mime_type}",
        ) from exc
    parts.append(
        types.Part(
            text=f"{ATTACHMENT_TEXT_MARKER}[Attached file: {filename}]\n\n{text}"
        ),
    )
    return parts


def build_user_message_parts(
    text: str,
    attachments: list[dict[str, Any]],
    attachment_bytes: list[bytes],
    *,
    model_id: str,
) -> list[types.Part]:
    """Assemble all parts for a user turn (text + files)."""
    parts: list[types.Part] = []
    trimmed = text.strip()
    if trimmed:
        parts.append(types.Part(text=trimmed))

    for attachment, data in zip(attachments, attachment_bytes, strict=True):
        parts.extend(
            build_parts_for_attachment(attachment, data, model_id=model_id),
        )

    if not parts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message must include text or at least one attachment",
        )
    return parts
