"""Tests for provider API key resolution."""

import pytest


def test_get_model_provider_from_prefix():
    from config.llm_keys import get_model_provider

    assert get_model_provider("openai/gpt-4o") == "openai"
    assert get_model_provider("gemini/gemini-2.0-flash") == "gemini"
    assert get_model_provider("anthropic/claude-3-5-sonnet-20241022") == "anthropic"


def test_get_api_key_for_model(monkeypatch):
    from config.llm_keys import get_api_key_for_model

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert get_api_key_for_model("anthropic/claude-3-5-haiku-latest") == "sk-ant-test"


def test_get_api_key_for_model_missing(monkeypatch):
    from config.llm_keys import MissingApiKeyError, get_api_key_for_model

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError, match="OPENAI_API_KEY"):
        get_api_key_for_model("openai/gpt-4o")
