"""
Google Workspace tools (Calendar + Tasks) scoped to the signed-in user.

Each function loads that user's stored OAuth tokens via ``google_client``. If
they have not connected Google yet, the tool returns a friendly ``connected:
False`` payload so the assistant can ask them to connect in Settings.
"""

from datetime import datetime, timedelta, timezone

from .context import require_user_id
from .google_client import get_calendar_service, get_tasks_service

_NOT_CONNECTED = {
    "connected": False,
    "message": (
        "Google Workspace is not connected. Ask the user to open Settings and "
        "click Connect Google to link their Calendar and Tasks."
    ),
}


def _add_days(iso_date: str, delta: int) -> str:
    """Shift an ISO ``YYYY-MM-DD`` date by ``delta`` days."""
    year, month, day = iso_date.split("-")
    shifted = datetime(int(year), int(month), int(day), tzinfo=timezone.utc) + timedelta(
        days=delta
    )
    return shifted.strftime("%Y-%m-%d")


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
        return dict(_NOT_CONNECTED)

    safe_limit = max(1, min(int(max_results), 50))
    try:
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=_parse_rfc3339(time_min),
                timeMax=_parse_rfc3339(time_max),
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
        return dict(_NOT_CONNECTED)

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
        start_body = {"dateTime": _parse_rfc3339(start_text)}
        end_body = {"dateTime": _parse_rfc3339(end_text)}

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


def list_tasks(show_completed: bool = False, max_results: int = 20) -> dict:
    """List tasks from the user's default Google Tasks list.

    Args:
        show_completed: Include completed tasks. Defaults to ``False``.
        max_results: Maximum tasks to return (1-50). Defaults to 20.

    Returns:
        A dict with ``count`` and ``tasks`` (id, title, notes, due, status).
    """
    user_id = require_user_id()
    service = get_tasks_service(user_id)
    if service is None:
        return dict(_NOT_CONNECTED)

    safe_limit = max(1, min(int(max_results), 50))
    try:
        result = (
            service.tasks()
            .list(
                tasklist="@default",
                showCompleted=bool(show_completed),
                maxResults=safe_limit,
            )
            .execute()
        )
    except Exception as exc:
        return {"connected": True, "error": str(exc)}

    tasks = []
    for item in result.get("items", []):
        tasks.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "notes": item.get("notes"),
                "due": item.get("due"),
                "status": item.get("status"),
            }
        )
    return {"connected": True, "count": len(tasks), "tasks": tasks}


def create_task(title: str, notes: str = "", due: str = "") -> dict:
    """Create a task on the user's default Google Tasks list.

    Args:
        title: Task title.
        notes: Optional notes/description.
        due: Optional due date/time as ISO/RFC3339 (date-only ``YYYY-MM-DD`` ok).

    Returns:
        The created task's ``id``, ``title``, ``due``, and ``status``.
    """
    user_id = require_user_id()
    service = get_tasks_service(user_id)
    if service is None:
        return dict(_NOT_CONNECTED)

    task_title = (title or "").strip()
    if not task_title:
        return {"connected": True, "error": "title is required"}

    body: dict = {"title": task_title}
    if notes.strip():
        body["notes"] = notes.strip()
    if due.strip():
        due_text = due.strip()
        if len(due_text) == 10:
            body["due"] = f"{due_text}T00:00:00.000Z"
        else:
            body["due"] = _parse_rfc3339(due_text)

    try:
        created = (
            service.tasks()
            .insert(tasklist="@default", body=body)
            .execute()
        )
    except Exception as exc:
        return {"connected": True, "error": str(exc)}

    return {
        "connected": True,
        "created": True,
        "id": created.get("id"),
        "title": created.get("title"),
        "due": created.get("due"),
        "status": created.get("status"),
    }


def complete_task(task_id: str) -> dict:
    """Mark a task on the default list as completed.

    Args:
        task_id: The Google Tasks task id (from ``list_tasks``).

    Returns:
        Confirmation with the updated task ``id`` and ``status``.
    """
    user_id = require_user_id()
    service = get_tasks_service(user_id)
    if service is None:
        return dict(_NOT_CONNECTED)

    task_id_text = (task_id or "").strip()
    if not task_id_text:
        return {"connected": True, "error": "task_id is required"}

    try:
        updated = (
            service.tasks()
            .patch(
                tasklist="@default",
                task=task_id_text,
                body={"status": "completed"},
            )
            .execute()
        )
    except Exception as exc:
        return {"connected": True, "error": str(exc)}

    return {
        "connected": True,
        "completed": True,
        "id": updated.get("id"),
        "title": updated.get("title"),
        "status": updated.get("status"),
    }
