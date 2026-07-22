"""
Google Workspace tools (Calendar) scoped to the signed-in user.

Each function loads that user's stored OAuth tokens via ``google_client``. If
they have not connected Google yet, the tool returns a friendly ``connected:
False`` payload so the assistant can ask them to connect in Settings.
"""

from datetime import datetime, timedelta, timezone

from ..context import require_user_id
from .google_client import get_calendar_service
from .utils import parse_rfc3339, NOT_CONNECTED


def _add_days(iso_date: str, delta: int) -> str:
    """Shift an ISO ``YYYY-MM-DD`` date by ``delta`` days."""
    year, month, day = iso_date.split("-")
    shifted = datetime(int(year), int(month), int(day), tzinfo=timezone.utc) + timedelta(
        days=delta
    )
    return shifted.strftime("%Y-%m-%d")


def list_calendar_events(
    time_min: str,
    time_max: str,
    max_results: int = 20,
) -> dict:
    """List the user's Google Calendar events in a date/time range.

    Args:
        time_min: Range start as ISO/RFC3339 (e.g. ``2026-07-12T00:00:00+05:30``).
        time_max: Range end as ISO/RFC3339.
        max_results: Maximum events to return (1-50). Defaults to 20.

    Returns:
        A dict with ``count`` and ``events`` (summary, start, end, id, location).
    """
    user_id = require_user_id()
    service = get_calendar_service(user_id)
    if service is None:
        return dict(NOT_CONNECTED)

    safe_limit = max(1, min(int(max_results), 50))
    try:
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=parse_rfc3339(time_min),
                timeMax=parse_rfc3339(time_max),
                maxResults=safe_limit,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except Exception as exc:
        return {"connected": True, "error": str(exc)}

    events = []
    for item in result.get("items", []):
        start = item.get("start", {})
        end = item.get("end", {})
        events.append(
            {
                "id": item.get("id"),
                "summary": item.get("summary"),
                "description": item.get("description"),
                "location": item.get("location"),
                "start": start.get("dateTime") or start.get("date"),
                "end": end.get("dateTime") or end.get("date"),
                "status": item.get("status"),
            }
        )
    return {"connected": True, "count": len(events), "events": events}


def create_calendar_event(
    summary: str,
    start: str,
    end: str,
    description: str = "",
    location: str = "",
) -> dict:
    """Create a new event on the user's primary Google Calendar.

    Args:
        summary: Event title.
        start: Start time as ISO/RFC3339, or ``YYYY-MM-DD`` for an all-day event.
        end: End time in the same format as ``start``.
        description: Optional event notes.
        location: Optional location string.

    Returns:
        The created event's ``id``, ``summary``, ``start``, and ``htmlLink``.
    """
    user_id = require_user_id()
    service = get_calendar_service(user_id)
    if service is None:
        return dict(NOT_CONNECTED)

    title = (summary or "").strip()
    if not title:
        return {"connected": True, "error": "summary is required"}

    start_text = (start or "").strip()
    end_text = (end or "").strip()
    if not start_text or not end_text:
        return {"connected": True, "error": "start and end are required"}

    if len(start_text) == 10 and len(end_text) == 10:
        # Google Calendar all-day events use an exclusive end date.
        end_date = end_text if end_text > start_text else _add_days(start_text, 1)
        start_body = {"date": start_text}
        end_body = {"date": end_date}
    else:
        start_body = {"dateTime": parse_rfc3339(start_text)}
        end_body = {"dateTime": parse_rfc3339(end_text)}

    body: dict = {
        "summary": title,
        "start": start_body,
        "end": end_body,
    }
    if description.strip():
        body["description"] = description.strip()
    if location.strip():
        body["location"] = location.strip()

    try:
        created = (
            service.events()
            .insert(calendarId="primary", body=body)
            .execute()
        )
    except Exception as exc:
        return {"connected": True, "error": str(exc)}

    start_val = created.get("start", {})
    return {
        "connected": True,
        "created": True,
        "id": created.get("id"),
        "summary": created.get("summary"),
        "start": start_val.get("dateTime") or start_val.get("date"),
        "htmlLink": created.get("htmlLink"),
    }
