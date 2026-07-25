"""Unit tests for chat tool event extraction."""

from types import SimpleNamespace

from api.v1.chat_api.tool_events import tool_events_from_adk, tool_steps_from_session_events


def test_tool_events_from_function_call_and_response():
    call = SimpleNamespace(id="fc-1", name="web_search", args={"query": "test"})
    response = SimpleNamespace(id="fc-1", name="web_search", response={"ok": True})
    event = SimpleNamespace(
        id="evt-1",
        get_function_calls=lambda: [call],
        get_function_responses=lambda: [],
    )
    resp_event = SimpleNamespace(
        id="evt-2",
        get_function_calls=lambda: [],
        get_function_responses=lambda: [response],
    )

    assert tool_events_from_adk(event) == [
        {
            "id": "fc-1",
            "name": "web_search",
            "status": "running",
            "args": {"query": "test"},
        }
    ]
    assert tool_events_from_adk(resp_event) == [
        {"id": "fc-1", "name": "web_search", "status": "done"}
    ]


def test_tool_steps_attach_to_next_assistant_message():
    call = SimpleNamespace(id="fc-1", name="list_my_goals", args={})
    response = SimpleNamespace(id="fc-1", name="list_my_goals", response={})
    events = [
        SimpleNamespace(
            id="u-1",
            content=SimpleNamespace(role="user", parts=[SimpleNamespace(text="goals")]),
            get_function_calls=lambda: [],
            get_function_responses=lambda: [],
        ),
        SimpleNamespace(
            id="m-call",
            content=SimpleNamespace(role="model", parts=[]),
            get_function_calls=lambda: [call],
            get_function_responses=lambda: [],
        ),
        SimpleNamespace(
            id="m-resp",
            content=SimpleNamespace(role="user", parts=[]),
            get_function_calls=lambda: [],
            get_function_responses=lambda: [response],
        ),
        SimpleNamespace(
            id="m-1",
            content=SimpleNamespace(
                role="model",
                parts=[SimpleNamespace(text="You have no goals.")],
            ),
            get_function_calls=lambda: [],
            get_function_responses=lambda: [],
        ),
    ]

    attached = tool_steps_from_session_events(events)
    assert attached[3] == [
        {
            "id": "fc-1",
            "name": "list_my_goals",
            "status": "done",
            "args": {},
        }
    ]
