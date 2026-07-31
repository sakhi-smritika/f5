"""Tests for provider API key resolution."""

import pytest


def test_get_model_provider_from_prefix():
    from config.llm_keys import get_model_provider

    assert get_model_provider("openai/gpt-4o") == "openai"
    assert get_model_provider("gemini/gemini-2.0-flash") == "gemini"
    assert get_model_provider("anthropic/claude-3-5-sonnet-20241022") == "anthropic"
    assert get_model_provider("ollama/qwen2.5:0.5b") == "ollama"
    assert get_model_provider("ollama_chat/qwen2.5:0.5b") == "ollama"


def test_get_api_key_for_model(monkeypatch):
    from config.llm_keys import get_api_key_for_model

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert get_api_key_for_model("anthropic/claude-3-5-haiku-latest") == "sk-ant-test"


def test_get_api_key_for_model_missing(monkeypatch):
    from config.llm_keys import MissingApiKeyError, get_api_key_for_model

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError, match="OPENAI_API_KEY"):
        get_api_key_for_model("openai/gpt-4o")


def test_get_api_key_for_ollama_without_env(monkeypatch):
    from config.llm_keys import get_api_key_for_model

    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    assert get_api_key_for_model("ollama_chat/qwen2.5:0.5b") == "ollama"


def test_get_ollama_base_url_default(monkeypatch):
    import os

    from config.llm_keys import DEFAULT_OLLAMA_BASE_URL, get_ollama_base_url

    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    assert get_ollama_base_url() == DEFAULT_OLLAMA_BASE_URL
    assert os.environ["OLLAMA_API_BASE"] == DEFAULT_OLLAMA_BASE_URL


def test_get_ollama_base_url_from_env(monkeypatch):
    import os

    from config.llm_keys import get_ollama_base_url

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.internal:11434/")
    assert get_ollama_base_url() == "http://ollama.internal:11434"
    assert os.environ["OLLAMA_API_BASE"] == "http://ollama.internal:11434"


def test_get_litellm_kwargs_for_ollama(monkeypatch):
    from config.llm_keys import get_litellm_kwargs

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    kwargs = get_litellm_kwargs("ollama_chat/qwen2.5:0.5b")
    assert kwargs == {
        "model": "ollama_chat/qwen2.5:0.5b",
        "api_key": "ollama",
        "api_base": "http://localhost:11434",
    }


def test_get_litellm_kwargs_for_openai(monkeypatch):
    from config.llm_keys import get_litellm_kwargs

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    kwargs = get_litellm_kwargs("openai/gpt-4o")
    assert kwargs == {"model": "openai/gpt-4o", "api_key": "sk-test"}
