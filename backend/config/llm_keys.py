"""Map LiteLLM model strings to the correct provider API key."""

from __future__ import annotations

import os

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

PROVIDER_ENV_KEYS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


class MissingApiKeyError(ValueError):
    """Raised when the env var for a model's provider is not set."""


def get_ollama_base_url() -> str:
    """Return the Ollama server URL and sync LiteLLM's ``OLLAMA_API_BASE``."""
    raw = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).strip()
    base = raw.rstrip("/") if raw else DEFAULT_OLLAMA_BASE_URL
    # LiteLLM probes OLLAMA_API_BASE for model metadata and tool-calling support.
    os.environ["OLLAMA_API_BASE"] = base
    return base


def get_model_provider(model_id: str) -> str:
    """Return the provider slug for a LiteLLM model string."""
    normalized = model_id.strip()
    if not normalized:
        raise ValueError("Model id is empty")

    if "/" in normalized:
        provider = normalized.split("/", 1)[0].lower()
        if provider in ("ollama", "ollama_chat"):
            return "ollama"
        if provider in PROVIDER_ENV_KEYS:
            return provider

    lowered = normalized.lower()
    if lowered.startswith(("gpt-", "o1", "o3", "o4")):
        return "openai"
    if lowered.startswith("claude"):
        return "anthropic"
    if lowered.startswith("gemini"):
        return "gemini"

    raise ValueError(f"Unsupported or unknown model provider for: {model_id}")


def get_api_key_for_model(model_id: str) -> str:
    """Return the API key env value required for the given model."""
    provider = get_model_provider(model_id)
    if provider == "ollama":
        return os.getenv("OLLAMA_API_KEY", "ollama").strip() or "ollama"

    env_key = PROVIDER_ENV_KEYS[provider]
    api_key = os.getenv(env_key, "").strip()
    if not api_key:
        raise MissingApiKeyError(
            f"{env_key} is not set but is required for model {model_id}"
        )
    return api_key


def get_litellm_kwargs(model_id: str) -> dict[str, str]:
    """Build kwargs for LiteLLM completion calls and ADK ``LiteLlm``."""
    resolved = model_id.strip()
    kwargs: dict[str, str] = {
        "model": resolved,
        "api_key": get_api_key_for_model(resolved),
    }
    if get_model_provider(resolved) == "ollama":
        kwargs["api_base"] = get_ollama_base_url()
    return kwargs


def get_providers_for_models(model_ids: list[str]) -> set[str]:
    return {get_model_provider(model_id) for model_id in model_ids}
