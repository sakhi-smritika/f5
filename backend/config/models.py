"""Chat model catalog parsed from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

FALLBACK_MODEL_ID = "openai/gpt-4o"


@dataclass(frozen=True)
class ChatModel:
    id: str
    label: str
    is_default: bool


def _parse_chat_models(raw: str) -> list[ChatModel]:
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()

    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue

        if "|" in entry:
            model_id, label = entry.split("|", 1)
        else:
            model_id, label = entry, entry

        model_id = model_id.strip()
        label = label.strip() or model_id
        if not model_id or model_id in seen:
            continue

        seen.add(model_id)
        entries.append((model_id, label))

    return [
        ChatModel(id=model_id, label=label, is_default=index == 0)
        for index, (model_id, label) in enumerate(entries)
    ]


def get_available_models() -> list[ChatModel]:
    """Return the configured chat models for the UI."""
    raw = os.getenv("CHAT_MODELS", "").strip()
    if raw:
        models = _parse_chat_models(raw)
        if models:
            return models

    return [ChatModel(id=FALLBACK_MODEL_ID, label=FALLBACK_MODEL_ID, is_default=True)]


def get_default_model_id() -> str:
    """Return the default model — the first entry in CHAT_MODELS."""
    return get_available_models()[0].id


def resolve_model(model_id: str | None) -> str:
    """Validate and return the model id to use for a chat turn."""
    if not model_id or not model_id.strip():
        return get_default_model_id()

    normalized = model_id.strip()
    allowed = {model.id for model in get_available_models()}
    if normalized not in allowed:
        raise ValueError(f"Unknown model: {normalized}")
    return normalized
