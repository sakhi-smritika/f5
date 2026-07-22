import json
from datetime import datetime, timezone

from .constants import DEFAULT_TITLE
from .schemas import SendMessageBody


def derive_title(text: str) -> str:
    """Build a short conversation title from the first user message."""
    first_line = text.strip().splitlines()[0] if text.strip() else DEFAULT_TITLE
    first_line = first_line.strip()
    if len(first_line) > 40:
        return first_line[:40].rstrip() + "..."
    return first_line or DEFAULT_TITLE


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def build_now_label(body: SendMessageBody) -> str:
    """Build a human-readable current-date label from the client's clock."""
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


def build_location_label(body: SendMessageBody) -> str | None:
    location = (body.client_location or "").strip()
    return location or None


def stream_error_message(exc: Exception, model_id: str) -> str:
    """Turn an LLM exception into a short client-facing message."""
    message = str(exc)
    if "not_found_error" in message or "NotFoundError" in type(exc).__name__:
        return (
            f"Model not available: {model_id}. Check CHAT_MODELS uses a valid "
            "model id for your API key."
        )
    if "authentication" in message.lower() or "api_key" in message.lower():
        return "Invalid or missing API key for the selected model's provider."
    trimmed = message.strip()
    if trimmed and len(trimmed) <= 200:
        return trimmed
    if trimmed:
        return trimmed[:200] + "..."
    return "The assistant failed to respond."
