"""Tests for the chat endpoints.

The ADK runner/session service and the Supabase service client are faked so the
router logic (ownership checks, SSE framing, title derivation) can be tested
without a database, an LLM, or network access.
"""

from types import SimpleNamespace

import pytest


class FakeSessionService:
    def __init__(self, session=None):
        self.session = session
        self.created: list[str] = []
        self.deleted: list[str] = []

    async def create_session(self, *, app_name, user_id, session_id):
        self.created.append(session_id)
        return SimpleNamespace(id=session_id)

    async def get_session(self, *, app_name, user_id, session_id):
        return self.session

    async def delete_session(self, *, app_name, user_id, session_id):
        self.deleted.append(session_id)


class FakeEvent:
    def __init__(self, text, *, partial, final, role="model"):
        self.content = SimpleNamespace(
            role=role, parts=[SimpleNamespace(text=text)]
        )
        self.partial = partial
        self._final = final

    def is_final_response(self):
        return self._final


class FakeRunner:
    def __init__(self, events):
        self._events = events

    def run_async(self, *, user_id, session_id, new_message, run_config):
        events = self._events

        async def generator():
            for event in events:
                yield event

        return generator()


class FakeTable:
    def __init__(self, select_data):
        self._select_data = select_data
        self.inserted: list[dict] = []
        self.updated: list[dict] = []
        self.deleted = False
        self._op = None

    def select(self, *args, **kwargs):
        self._op = "select"
        return self

    def insert(self, row):
        self._op = "insert"
        self.inserted.append(row)
        return self

    def update(self, values):
        self._op = "update"
        self.updated.append(values)
        return self

    def delete(self):
        self._op = "delete"
        self.deleted = True
        return self

    def eq(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        if self._op == "select":
            return SimpleNamespace(data=self._select_data)
        return SimpleNamespace(data=[])


class FakeSupabase:
    def __init__(self, select_data):
        self.table_obj = FakeTable(select_data)

    def table(self, name):
        return self.table_obj


OWNED_ROW = [{"id": "conv-1", "user_id": "test-user-id", "title": "New chat"}]


@pytest.fixture
def patch_chat(monkeypatch):
    """Helper to install fakes into the chat module namespace."""
    import api.v1.chat as chat

    def apply(*, session_service=None, runner=None, supabase=None):
        if session_service is not None:
            monkeypatch.setattr(chat, "get_session_service", lambda: session_service)
        if runner is not None:
            monkeypatch.setattr(chat, "get_runner", lambda model_id=None: runner)
        if supabase is not None:
            monkeypatch.setattr(chat, "get_supabase_service_client", lambda: supabase)

    return apply


def test_create_conversation_requires_auth(unauthenticated_client):
    response = unauthenticated_client.post("/api/v1/chat/conversations", json={})
    assert response.status_code == 401


def test_create_conversation(client, patch_chat):
    session_service = FakeSessionService()
    supabase = FakeSupabase(select_data=[])
    patch_chat(session_service=session_service, supabase=supabase)

    response = client.post("/api/v1/chat/conversations", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New chat"
    assert body["id"]
    # An ADK session and a metadata row were created with the same id.
    assert session_service.created == [body["id"]]
    assert supabase.table_obj.inserted[0]["id"] == body["id"]
    assert supabase.table_obj.inserted[0]["user_id"] == "test-user-id"


def test_get_messages_unknown_conversation_returns_404(client, patch_chat):
    patch_chat(
        session_service=FakeSessionService(session=None),
        supabase=FakeSupabase(select_data=[]),
    )

    response = client.get("/api/v1/chat/conversations/conv-1/messages")

    assert response.status_code == 404


def test_get_messages_maps_events(client, patch_chat):
    session = SimpleNamespace(
        events=[
            FakeEvent("hi there", partial=False, final=True, role="user"),
            FakeEvent("hello!", partial=False, final=True, role="model"),
        ]
    )
    patch_chat(
        session_service=FakeSessionService(session=session),
        supabase=FakeSupabase(select_data=OWNED_ROW),
    )

    response = client.get("/api/v1/chat/conversations/conv-1/messages")

    assert response.status_code == 200
    assert response.json() == {
        "messages": [
            {"role": "user", "text": "hi there"},
            {"role": "assistant", "text": "hello!"},
        ]
    }


def test_send_message_streams_sse_and_sets_title(client, patch_chat):
    runner = FakeRunner(
        [
            FakeEvent("Hello", partial=True, final=False),
            FakeEvent(" world", partial=True, final=False),
            FakeEvent("Hello world", partial=False, final=True),
        ]
    )
    supabase = FakeSupabase(select_data=OWNED_ROW)
    patch_chat(
        session_service=FakeSessionService(session=SimpleNamespace(events=[])),
        runner=runner,
        supabase=supabase,
    )

    response = client.post(
        "/api/v1/chat/conversations/conv-1/messages",
        json={"text": "what is up"},
    )

    assert response.status_code == 200
    body = response.text
    # Partial deltas streamed, aggregated final not double-counted.
    assert '"delta": "Hello"' in body
    assert '"delta": " world"' in body
    assert '"done": true' in body
    # First turn derived a title from the user's message.
    assert supabase.table_obj.updated[0]["title"] == "what is up"


def test_send_message_rejects_unknown_model(client, patch_chat, monkeypatch):
    monkeypatch.setenv(
        "CHAT_MODELS",
        "openai/gpt-4o|GPT-4o",
    )
    patch_chat(
        session_service=FakeSessionService(session=SimpleNamespace(events=[])),
        runner=FakeRunner([]),
        supabase=FakeSupabase(select_data=OWNED_ROW),
    )

    response = client.post(
        "/api/v1/chat/conversations/conv-1/messages",
        json={"text": "hello", "model": "openai/unknown"},
    )

    assert response.status_code == 422
    session_service = FakeSessionService(session=SimpleNamespace(events=[]))
    supabase = FakeSupabase(select_data=OWNED_ROW)
    patch_chat(session_service=session_service, supabase=supabase)

    response = client.delete("/api/v1/chat/conversations/conv-1")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert session_service.deleted == ["conv-1"]
    assert supabase.table_obj.deleted is True
