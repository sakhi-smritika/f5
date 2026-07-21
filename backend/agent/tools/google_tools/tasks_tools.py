"""
Google Workspace tools (Calendar) scoped to the signed-in user.

Each function loads that user's stored OAuth tokens via ``google_client``. If
they have not connected Google yet, the tool returns a friendly ``connected:
False`` payload so the assistant can ask them to connect in Settings.
"""

from ..context import require_user_id
from .google_client import get_calendar_service, get_tasks_service
from .utils import _parse_rfc3339

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
