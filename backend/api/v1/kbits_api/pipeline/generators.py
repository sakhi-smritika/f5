"""Generator strategies: turn a ``Query`` into candidate bits.

The query stage decides *what kind* of bits the user needs; a generator produces
them. ``LLMGenerator`` (the default) asks a LiteLLM-backed model.
"""

from __future__ import annotations

import json
import logging

import litellm

from config.llm_keys import get_litellm_kwargs
from config.models import get_default_model_id

from .base import GeneratorStrategy, KBCandidate, Query, Registry

logger = logging.getLogger(__name__)

GENERATOR_STRATEGIES: Registry[GeneratorStrategy] = Registry("generator")

# Used when the query stage produced nothing to go on (no goals, empty profile).
_FALLBACK_FOCUS = "General personal-growth knowledge."

_SYSTEM_PROMPT = (
    "You produce short, high-signal knowledge bits for a personal-growth app. "
    "Each bit is a self-contained, readable snippet the user can consume in under "
    "a minute instead of doom-scrolling social media. Bits must be concrete and "
    "relevant to the user's stated focus, and must not repeat anything in the "
    "avoid list. When the query includes context on what the user needs now, "
    "treat it as ground truth about their situation and draw each bit from it. "
    "Respond with ONLY a JSON array of objects, each with exactly "
    '"title" (a short headline) and "content" (2-5 sentences of plain text). '
    "No markdown fences, no commentary."
)


def _generator_query_text(query: Query) -> str:
    """Flatten the query for the generator without listing titles to copy."""
    parts: list[str] = []
    if query.include:
        parts.append("Focus on: " + "; ".join(query.include))
    if query.exclude:
        parts.append(
            f"The user already has {len(query.exclude)} related bits. "
            "Do not reuse or lightly rephrase any existing title — invent fresh angles."
        )
    if query.brief:
        parts.append("What this user needs now:\n" + query.brief)
    return "\n".join(parts)


def build_generator_user_message(query: Query, limit: int) -> str:
    """Build the user message sent to the LLM generator for one invoke run."""
    query_text = _generator_query_text(query) or _FALLBACK_FOCUS
    parts = [f"Generate {limit} knowledge bits.", "", query_text]
    if query.rejected_titles:
        parts.extend(
            [
                "",
                "Your previous titles were rejected because they duplicate existing bits.",
                "Use fresh angles and different titles. Rejected titles:",
                *[f"- {title}" for title in query.rejected_titles[:20]],
            ]
        )
    return "\n".join(parts)


def _parse_bits(raw: str, limit: int) -> list[KBCandidate]:
    """Parse the model's response into candidates, tolerating stray fences."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        # Drop a leading language tag like ``json`` if present.
        newline = text.find("\n")
        if newline != -1:
            text = text[newline + 1 :]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        preview = text[:240].replace("\n", "\\n")
        logger.warning(
            "LLMGenerator returned non-JSON content; skipping",
            extra={"response_preview": preview},
        )
        return []

    if not isinstance(data, list):
        return []

    candidates: list[KBCandidate] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip()
        if title and content:
            candidates.append(KBCandidate(title=title, content=content))
        if len(candidates) >= limit:
            break
    return candidates


@GENERATOR_STRATEGIES.register("llm", default=True)
class LLMGenerator:
    """Default generator: ask a LiteLLM-backed model to write the bits."""

    async def generate(self, query: Query, limit: int) -> list[KBCandidate]:
        user_message = build_generator_user_message(query, limit)
        response = await litellm.acompletion(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            **get_litellm_kwargs(get_default_model_id()),
        )
        content = (
            response.choices[0].message.content
            if response.choices and response.choices[0].message.content
            else ""
        )
        return _parse_bits(content, limit)
