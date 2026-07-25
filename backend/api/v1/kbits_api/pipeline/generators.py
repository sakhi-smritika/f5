"""Generator strategies: turn a ``Query`` into candidate bits.

The query stage decides *what kind* of bits the user needs; a generator produces
them. ``LLMGenerator`` (the default) asks a LiteLLM-backed model.
``WebSearchGenerator`` is a registered stub kept behind the same contract so a
web-grounded generator can drop in later without touching the orchestrator or
endpoints.
"""

from __future__ import annotations

import json
import logging

import litellm

from config.llm_keys import get_api_key_for_model
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
        logger.warning("LLMGenerator returned non-JSON content; skipping")
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
        query_text = query.to_text() or _FALLBACK_FOCUS
        model_id = get_default_model_id()
        response = await litellm.acompletion(
            model=model_id,
            api_key=get_api_key_for_model(model_id),
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Generate {limit} knowledge bits.\n\n{query_text}",
                },
            ],
        )
        content = (
            response.choices[0].message.content
            if response.choices and response.choices[0].message.content
            else ""
        )
        return _parse_bits(content, limit)


@GENERATOR_STRATEGIES.register("web_search")
class WebSearchGenerator:
    """Placeholder for a future web-search-grounded generator.

    Registered so it appears in ``GET /kbits/strategies`` and documents the
    intended extension point. Wire a search API + summarizer here later.
    """

    async def generate(self, query: Query, limit: int) -> list[KBCandidate]:
        raise NotImplementedError(
            "web_search generator is not implemented yet; use 'llm'."
        )
