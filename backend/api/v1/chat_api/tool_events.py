"""Extract tool-call / tool-result payloads from ADK events for chat clients."""

from __future__ import annotations

import json
from typing import Any


def _jsonable(value: Any) -> Any:
    """Best-effort conversion of tool args/response into JSON-serializable data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _call_id(call: Any, fallback: str) -> str:
    call_id = getattr(call, "id", None)
    if call_id:
        return str(call_id)
    return fallback


def tool_events_from_adk(event: Any) -> list[dict]:
    """Return SSE ``tool`` payloads for function calls / responses on ``event``.

    Each payload: ``{id, name, status, args?}`` where status is ``running`` or
    ``done``. MCP and native FunctionTools look the same after ADK conversion.
    """
    payloads: list[dict] = []

    get_calls = getattr(event, "get_function_calls", None)
    get_responses = getattr(event, "get_function_responses", None)

    calls = get_calls() if callable(get_calls) else []
    for index, call in enumerate(calls):
        name = getattr(call, "name", None) or "tool"
        payloads.append(
            {
                "id": _call_id(call, f"{getattr(event, 'id', 'evt')}-call-{index}"),
                "name": name,
                "status": "running",
                "args": _jsonable(getattr(call, "args", None) or {}),
            }
        )

    responses = get_responses() if callable(get_responses) else []
    for index, response in enumerate(responses):
        name = getattr(response, "name", None) or "tool"
        # A function response means the tool finished (success or soft failure
        # is conveyed inside the response payload; clients treat it as done).
        payloads.append(
            {
                "id": _call_id(
                    response, f"{getattr(event, 'id', 'evt')}-resp-{index}"
                ),
                "name": name,
                "status": "done",
            }
        )

    return payloads


def tool_steps_from_session_events(events: list[Any]) -> list[dict]:
    """Rebuild completed tool steps from a session's event history.

    Returns a parallel list (same length as ``events``) where each entry is the
    list of tool steps that should be attached when that event becomes an
    assistant text message. Steps accumulate across function-call/response
    events and attach to the next model text event.
    """
    pending: list[dict] = []
    by_id: dict[str, dict] = {}
    attached: list[list[dict]] = [[] for _ in events]

    for index, event in enumerate(events):
        for payload in tool_events_from_adk(event):
            tool_id = payload["id"]
            existing = by_id.get(tool_id)
            if existing is None:
                step = {
                    "id": tool_id,
                    "name": payload["name"],
                    "status": payload["status"],
                    "args": payload.get("args") or {},
                }
                pending.append(step)
                by_id[tool_id] = step
            else:
                existing["status"] = payload["status"]
                if "args" in payload and payload["args"]:
                    existing["args"] = payload["args"]

        content = getattr(event, "content", None)
        role = getattr(content, "role", None) if content else None
        parts = getattr(content, "parts", None) if content else None
        text = ""
        if parts:
            text = "".join(
                getattr(part, "text", None) or ""
                for part in parts
                if getattr(part, "text", None)
            )
        if role == "model" and text.strip() and pending:
            # Snapshot completed steps onto this assistant message.
            attached[index] = [
                {
                    "id": step["id"],
                    "name": step["name"],
                    "status": "done" if step["status"] == "running" else step["status"],
                    "args": step.get("args") or {},
                }
                for step in pending
            ]
            pending = []
            by_id = {}

    return attached
