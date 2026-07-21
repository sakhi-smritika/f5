from datetime import datetime, timezone

def _parse_rfc3339(value: str) -> str:
    """Normalize an ISO/RFC3339 timestamp for the Google APIs."""
    text = (value or "").strip()
    if not text:
        raise ValueError("Empty datetime")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()