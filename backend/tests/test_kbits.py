"""Tests for the knowledge-bits (kbits) endpoints and strategy pipeline.

The Supabase service client and the LLM generator are faked so the router logic,
strategy resolution, and pipeline wiring can be tested without a database or an
LLM. External dependencies are patched at their import site in each submodule.
"""

from types import SimpleNamespace

import pytest


class FakeTable:
    """Minimal Supabase table double supporting the chained calls we use."""

    def __init__(self, select_data=None):
        self._select_data = select_data or []
        self.inserted: list[dict] = []
        self.updated: list[dict] = []
        self.deleted = False
        self._op = None
        self._last_insert = None

    def select(self, *args, **kwargs):
        self._op = "select"
        return self

    def insert(self, rows):
        self._op = "insert"
        as_list = rows if isinstance(rows, list) else [rows]
        self.inserted.extend(as_list)
        self._last_insert = as_list
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

    def order(self, *args, **kwargs):
        return self

    def range(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def is_(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    @property
    def not_(self):
        return self

    def execute(self):
        if self._op == "select":
            return SimpleNamespace(data=self._select_data)
        if self._op == "insert":
            return SimpleNamespace(data=self._last_insert or [])
        return SimpleNamespace(data=[])


class FakeSupabase:
    def __init__(self, tables=None):
        self.tables = {
            name: FakeTable(data) for name, data in (tables or {}).items()
        }

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = FakeTable([])
        return self.tables[name]


def _fake_llm(json_content: str):
    """Stand in for the ``litellm`` module; generators await ``acompletion``."""
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json_content))]
    )

    async def acompletion(**kwargs):
        return response

    return SimpleNamespace(acompletion=acompletion)


@pytest.fixture
def patch_kbits(monkeypatch):
    """Install a shared FakeSupabase across the kbits modules that read/write it."""

    def apply(supabase):
        for module in (
            "api.v1.kbits_api.access",
            "api.v1.kbits_api.bits",
            "api.v1.kbits_api.pipeline.orchestrator",
        ):
            monkeypatch.setattr(
                f"{module}.get_supabase_service_client", lambda: supabase
            )
        return supabase

    return apply


OWNED_BIT = [{"id": "bit-1", "user_id": "test-user-id", "title": "T", "content": "C"}]


# --- auth -------------------------------------------------------------------


def test_feed_requires_auth(unauthenticated_client):
    assert unauthenticated_client.get("/api/v1/kbits").status_code == 401


def test_invoke_requires_auth(unauthenticated_client):
    assert unauthenticated_client.post("/api/v1/kbits/invoke", json={}).status_code == 401


# --- strategies -------------------------------------------------------------


def test_list_strategies(client):
    response = client.get("/api/v1/kbits/strategies")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"query", "generator", "screen", "rank"}
    assert body["generator"]["default"] == "llm"
    assert "web_search" in body["generator"]["options"]
    assert body["query"]["default"] == "goals_profile"
    assert "agent" in body["query"]["options"]


# --- invoke -----------------------------------------------------------------


def test_invoke_llm_generator_inserts_parsed_bits(client, patch_kbits, monkeypatch):
    supabase = FakeSupabase(tables={"goals": [], "users": [], "knowledge_bits": []})
    patch_kbits(supabase)

    monkeypatch.setattr(
        "api.v1.kbits_api.pipeline.generators.litellm",
        _fake_llm('[{"title": "Focus", "content": "Deep work beats busywork."}]'),
    )
    monkeypatch.setattr(
        "api.v1.kbits_api.pipeline.generators.get_api_key_for_model",
        lambda model_id: "test-key",
    )

    response = client.post("/api/v1/kbits/invoke", json={"count": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["bits"][0]["title"] == "Focus"
    inserted = supabase.table("knowledge_bits").inserted
    assert inserted[0]["user_id"] == "test-user-id"
    assert inserted[0]["related_goal"] is None


def test_invoke_sets_related_goal(client, patch_kbits, monkeypatch):
    supabase = FakeSupabase(tables={"goals": [], "users": [], "knowledge_bits": []})
    patch_kbits(supabase)
    monkeypatch.setattr(
        "api.v1.kbits_api.pipeline.generators.litellm",
        _fake_llm('[{"title": "A", "content": "B"}]'),
    )
    monkeypatch.setattr(
        "api.v1.kbits_api.pipeline.generators.get_api_key_for_model",
        lambda model_id: "test-key",
    )

    response = client.post("/api/v1/kbits/invoke", json={"goal_id": "goal-9"})

    assert response.status_code == 200
    assert supabase.table("knowledge_bits").inserted[0]["related_goal"] == "goal-9"


def test_invoke_unknown_strategy_returns_422(client, patch_kbits):
    patch_kbits(FakeSupabase())
    response = client.post(
        "/api/v1/kbits/invoke", json={"rank_strategy": "does_not_exist"}
    )
    assert response.status_code == 422


def test_invoke_custom_registered_strategy_runs_end_to_end(client, patch_kbits):
    """Registering a new generator strategy makes it usable without other changes."""
    from api.v1.kbits_api.pipeline.base import KBCandidate
    from api.v1.kbits_api.pipeline.generators import GENERATOR_STRATEGIES

    class FakeGenerator:
        async def generate(self, query, limit):
            return [KBCandidate(title="fake", content="from a custom strategy")]

    GENERATOR_STRATEGIES._items["fake"] = FakeGenerator()
    try:
        supabase = FakeSupabase(
            tables={"goals": [], "users": [], "knowledge_bits": []}
        )
        patch_kbits(supabase)

        response = client.post(
            "/api/v1/kbits/invoke", json={"generator_strategy": "fake"}
        )

        assert response.status_code == 200
        assert response.json()["bits"][0]["title"] == "fake"
    finally:
        GENERATOR_STRATEGIES._items.pop("fake", None)


# --- agent query strategy ---------------------------------------------------


def _recording_llm(json_content: str, calls: list[dict]):
    """Fake ``litellm`` that records the messages each call received."""
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json_content))]
    )

    async def acompletion(**kwargs):
        calls.append(kwargs)
        return response

    return SimpleNamespace(acompletion=acompletion)


@pytest.fixture
def patch_agent_query(monkeypatch, patch_kbits):
    """Run the agent query strategy with the agent and generator both faked."""

    def apply(
        submitted,
        json_content='[{"title": "A", "content": "B"}]',
        existing_titles=(),
    ):
        supabase = FakeSupabase(
            tables={
                "goals": [],
                "users": [],
                "knowledge_bits": [{"title": t} for t in existing_titles],
            }
        )
        patch_kbits(supabase)

        calls: list[dict] = []
        monkeypatch.setattr(
            "api.v1.kbits_api.pipeline.generators.litellm",
            _recording_llm(json_content, calls),
        )
        monkeypatch.setattr(
            "api.v1.kbits_api.pipeline.generators.get_api_key_for_model",
            lambda model_id: "test-key",
        )

        async def fake_build(count, goal_id=None, **kwargs):
            calls.append({"query_agent": {"count": count, "goal_id": goal_id}})
            return submitted

        monkeypatch.setattr(
            "api.v1.kbits_api.pipeline.query.build_kbit_query", fake_build
        )
        return supabase, calls

    return apply


def _generator_prompt(calls: list[dict]) -> str:
    """The user message the generator received."""
    return next(c for c in calls if "messages" in c)["messages"][1]["content"]


def test_agent_query_reaches_the_generator(client, patch_agent_query):
    supabase, calls = patch_agent_query(
        {
            "include": ["deep work blocks"],
            "exclude": ["sleep hygiene"],
            "brief": "Their focus goal has stalled for two weeks.",
        }
    )

    response = client.post(
        "/api/v1/kbits/invoke", json={"query_strategy": "agent", "count": 4}
    )

    assert response.status_code == 200
    assert supabase.table("knowledge_bits").inserted[0]["title"] == "A"

    assert calls[0]["query_agent"] == {"count": 4, "goal_id": None}
    prompt = _generator_prompt(calls)
    assert "Focus on: deep work blocks" in prompt
    assert "Avoid repeating: sleep hygiene" in prompt
    assert "Their focus goal has stalled for two weeks." in prompt


def test_agent_query_merges_existing_titles_into_exclusions(
    client, patch_agent_query
):
    """Dedup does not depend on the agent remembering what it has already seen."""
    _, calls = patch_agent_query(
        {"include": ["x"], "exclude": ["sleep hygiene"], "brief": ""},
        json_content='[{"title": "Fresh", "content": "B"}]',
        existing_titles=["Known Bit"],
    )

    response = client.post(
        "/api/v1/kbits/invoke", json={"query_strategy": "agent"}
    )

    assert response.status_code == 200
    assert "sleep hygiene; Known Bit" in _generator_prompt(calls)


def test_agent_query_forwards_goal_id(client, patch_agent_query):
    _, calls = patch_agent_query({"include": ["x"], "exclude": [], "brief": ""})

    response = client.post(
        "/api/v1/kbits/invoke",
        json={"query_strategy": "agent", "goal_id": "goal-9"},
    )

    assert response.status_code == 200
    assert calls[0]["query_agent"]["goal_id"] == "goal-9"


def test_agent_query_falls_back_when_agent_submits_nothing(
    client, patch_agent_query
):
    supabase, calls = patch_agent_query(None, existing_titles=["Known Bit"])

    response = client.post(
        "/api/v1/kbits/invoke", json={"query_strategy": "agent"}
    )

    assert response.status_code == 200
    assert supabase.table("knowledge_bits").inserted[0]["title"] == "A"
    # goals_profile behaviour: exclusions from existing titles, no agent brief.
    prompt = _generator_prompt(calls)
    assert "Avoid repeating: Known Bit" in prompt
    assert "What this user needs right now" not in prompt


# --- feed / interactions ----------------------------------------------------


def test_feed_lists_bits(client, patch_kbits):
    supabase = FakeSupabase(tables={"knowledge_bits": OWNED_BIT})
    patch_kbits(supabase)

    response = client.get("/api/v1/kbits?limit=5")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["bits"][0]["id"] == "bit-1"


def test_patch_updates_flag(client, patch_kbits):
    supabase = FakeSupabase(tables={"knowledge_bits": OWNED_BIT})
    patch_kbits(supabase)

    response = client.patch("/api/v1/kbits/bit-1", json={"is_read": True})

    assert response.status_code == 200
    assert supabase.table("knowledge_bits").updated[0] == {"is_read": True}


def test_patch_rejects_out_of_range_rating(client, patch_kbits):
    supabase = FakeSupabase(tables={"knowledge_bits": OWNED_BIT})
    patch_kbits(supabase)

    response = client.patch("/api/v1/kbits/bit-1", json={"rating": 9})

    assert response.status_code == 422


def test_patch_rejects_non_updatable_only(client, patch_kbits):
    supabase = FakeSupabase(tables={"knowledge_bits": OWNED_BIT})
    patch_kbits(supabase)

    # ``title`` is not an interaction field; pydantic drops it, leaving no updates.
    response = client.patch("/api/v1/kbits/bit-1", json={"title": "hacked"})

    assert response.status_code == 422


def test_patch_unknown_bit_returns_404(client, patch_kbits):
    patch_kbits(FakeSupabase(tables={"knowledge_bits": []}))

    response = client.patch("/api/v1/kbits/missing", json={"is_read": True})

    assert response.status_code == 404


def test_delete_bit(client, patch_kbits):
    supabase = FakeSupabase(tables={"knowledge_bits": OWNED_BIT})
    patch_kbits(supabase)

    response = client.delete("/api/v1/kbits/bit-1")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert supabase.table("knowledge_bits").deleted is True


# --- pipeline units ---------------------------------------------------------


def test_text_screener_dedupes():
    from api.v1.kbits_api.pipeline.base import KBCandidate, PipelineContext
    from api.v1.kbits_api.pipeline.screener import TextScreener

    ctx = PipelineContext(user_id="u", existing_titles=["Known Bit"])
    candidates = [
        KBCandidate(title="Known Bit", content="dup vs existing"),
        KBCandidate(title="New One", content="fresh"),
        KBCandidate(title="new one", content="dup within batch"),
        KBCandidate(title="Empty", content="   "),
    ]

    kept = TextScreener().screen(candidates, ctx)

    assert [c.title for c in kept] == ["New One"]


def test_text_ranker_orders_by_overlap():
    from api.v1.kbits_api.pipeline.base import KBCandidate, Query
    from api.v1.kbits_api.pipeline.ranker import TextRanker

    query = Query(include=["python testing"])
    candidates = [
        KBCandidate(title="Cooking", content="pasta recipes"),
        KBCandidate(title="Python", content="testing with pytest"),
    ]

    ranked = TextRanker().rank(candidates, query)

    assert ranked[0].title == "Python"
