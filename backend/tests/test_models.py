"""Tests for the chat models catalog endpoint."""

import pytest


@pytest.fixture
def models_env(monkeypatch):
    monkeypatch.setenv(
        "CHAT_MODELS",
        "openai/gpt-4o|GPT-4o,openai/gpt-4o-mini|GPT-4o mini",
    )


def test_list_models_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/models")
    assert response.status_code == 401


def test_list_models(client, models_env):
    response = client.get("/api/v1/models")

    assert response.status_code == 200
    body = response.json()
    assert body["default"] == "openai/gpt-4o"
    assert body["models"] == [
        {"id": "openai/gpt-4o", "label": "GPT-4o", "is_default": True},
        {"id": "openai/gpt-4o-mini", "label": "GPT-4o mini", "is_default": False},
    ]


def test_resolve_model_rejects_unknown(models_env):
    from config.models import resolve_model

    with pytest.raises(ValueError, match="Unknown model"):
        resolve_model("openai/unknown")
