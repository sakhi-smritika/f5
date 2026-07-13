"""Map LiteLLM model strings to the correct provider API key."""

from __future__ import annotations

import os

PROVIDER_ENV_KEYS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


class MissingApiKeyError(ValueError):
    """Raised when the env var for a model's provider is not set."""


def get_model_provider(model_id: str) -> str:
    """Return the provider slug for a LiteLLM model string."""
    normalized = model_id.strip()
    if not normalized:
        raise ValueError("Model id is empty")

    if "/" in normalized:
        provider = normalized.split("/", 1)[0].lower()
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
    env_key = PROVIDER_ENV_KEYS[provider]
    api_key = os.getenv(env_key, "").strip()
    if not api_key:
        raise MissingApiKeyError(
            f"{env_key} is not set but is required for model {model_id}"
        )
    return api_key


def get_providers_for_models(model_ids: list[str]) -> set[str]:
    return {get_model_provider(model_id) for model_id in model_ids}
