"""LLM-backed concept extraction and graph enrichment after bit generation."""

from __future__ import annotations

import json
import logging

import litellm

from config.llm_keys import get_litellm_kwargs
from config.models import get_default_model_id

from .models import GraphSnapshot
from .store import link_bit_to_nodes, patch_bit_metadata, upsert_edge, upsert_node

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You extract related concept names from a short knowledge bit. "
    "Return ONLY a JSON array of 1-3 strings — each a concise concept name "
    "that the bit introduces or extends. No markdown, no commentary."
)


async def extract_concepts(
    *,
    title: str,
    content: str,
    expansion_label: str,
) -> list[str]:
    """Ask the model which new concepts a bit covers relative to the expansion node."""
    user_message = (
        f'Expansion concept: "{expansion_label}"\n'
        f'Title: "{title}"\n'
        f"Content: {content}\n\n"
        "List related concept names introduced by this bit."
    )
    try:
        response = await litellm.acompletion(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            **get_litellm_kwargs(get_default_model_id()),
        )
        raw = (
            response.choices[0].message.content
            if response.choices and response.choices[0].message.content
            else "[]"
        )
        return _parse_concept_list(raw)
    except Exception:
        logger.exception("Concept extraction failed")
        return []


async def enrich_persisted_bits(
    *,
    snapshot: GraphSnapshot,
    expansion_node_id: str,
    bits: list[dict],
    base_metadata: dict,
) -> None:
    """Grow the graph and write per-bit metadata after an invoke batch."""
    expansion = snapshot.node_by_id(expansion_node_id)
    if expansion is None:
        return

    for bit in bits:
        new_labels = await extract_concepts(
            title=bit.get("title") or "",
            content=bit.get("content") or "",
            expansion_label=expansion.label,
        )
        new_node_ids = [expansion_node_id]
        for label in new_labels:
            node = upsert_node(snapshot.id, label)
            upsert_edge(snapshot.id, expansion_node_id, node.id)
            new_node_ids.append(node.id)

        metadata = {
            **base_metadata,
            "new_concepts": new_labels,
        }
        patch_bit_metadata(bit["id"], metadata)
        bit["metadata"] = metadata
        link_bit_to_nodes(bit["id"], list(dict.fromkeys(new_node_ids)))


def _parse_concept_list(raw: str) -> list[str]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        newline = text.find("\n")
        if newline != -1:
            text = text[newline + 1 :]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item).strip() for item in data if str(item).strip()][:3]
