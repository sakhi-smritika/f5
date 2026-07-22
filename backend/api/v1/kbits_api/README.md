# Knowledge Bits (kbits) API

Serves readable, goal-relevant knowledge snippets ("bits") the user consumes
instead of doom-scrolling. Bits are stored in `public.knowledge_bits` and are
produced on demand by a four-stage strategy pipeline.

Mounted at `/api/v1/kbits` via `api/v1/router.py`.

## Layout

```
kbits_api/
├── README.md
├── __init__.py          # exports `router`
├── router.py            # composes sub-routers (no business logic)
├── schemas.py           # Pydantic request bodies
├── constants.py         # invoke counts, updatable-field whitelist, rating bounds
├── access.py            # ownership checks + read-only Supabase queries
├── bits.py              # feed + interaction routes (list/get/patch/delete)
├── invoke.py            # generate bits + list available strategies
└── pipeline/            # the generation pipeline (four strategy stages)
    ├── base.py          # Query, KBCandidate, PipelineContext, Protocols, Registry
    ├── query.py         # QUERY_STRATEGIES  (default: goals_profile)
    ├── sources.py       # SOURCE_STRATEGIES (default: llm; web_search stub)
    ├── screener.py      # SCREEN_STRATEGIES (default: text)
    ├── ranker.py        # RANK_STRATEGIES   (default: text)
    └── orchestrator.py  # resolve strategies -> build -> search -> screen -> rank -> insert
```

## Endpoints

| Method | Path | Module | Purpose |
|--------|------|--------|---------|
| `POST` | `/kbits/invoke` | `invoke.py` | Generate + persist bits |
| `GET` | `/kbits/strategies` | `invoke.py` | List strategies + defaults per stage |
| `GET` | `/kbits` | `bits.py` | Feed (newest first, filterable) |
| `GET` | `/kbits/{id}` | `bits.py` | Single bit |
| `PATCH` | `/kbits/{id}` | `bits.py` | Update interaction flags |
| `DELETE` | `/kbits/{id}` | `bits.py` | Delete a bit |

`invoke_router` is included before `bits_router` so the static `/strategies` and
`/invoke` paths resolve before the dynamic `/{kbit_id}` route.

### `POST /kbits/invoke`

```json
{
  "goal_id": "optional-uuid",
  "count": 5,
  "query_strategy": "goals_profile",
  "source_strategy": "llm",
  "screen_strategy": "text",
  "rank_strategy": "text"
}
```

Every `*_strategy` field is optional; omit it to use that stage's default. An
unknown strategy name returns `422`. When `goal_id` is set, the created bits are
linked to that goal via `related_goal`.

### `PATCH /kbits/{id}`

Only interaction fields may be set (`constants.UPDATABLE_FIELDS`): `is_read`,
`is_liked`, `is_disliked`, `rating` (1-5), `is_marked_relavant`,
`is_marked_irrelavant`. Title/content/timestamps are server-owned.

## The strategy pipeline

Each of the four stages is a **Strategy**: an interchangeable algorithm behind a
fixed input/output contract. Stages share `PipelineContext` (loaded once per
invoke: goals, profile, existing titles).

```
build(Query) -> search(SoK) -> screen -> rank -> insert
```

Contracts (see `pipeline/base.py`):

| Stage | Protocol | Signature |
|-------|----------|-----------|
| query | `QueryStrategy` | `build(ctx) -> Query` |
| source | `SourceStrategy` | `search(query, limit) -> list[KBCandidate]` |
| screen | `ScreenStrategy` | `screen(candidates, ctx) -> list[KBCandidate]` |
| rank | `RankStrategy` | `rank(candidates, query) -> list[KBCandidate]` |

Each stage module owns a `Registry` and registers strategies by name, marking
one as the default.

### Adding a strategy

```python
from .base import KBCandidate, Query, Registry
from .ranker import RANK_STRATEGIES

@RANK_STRATEGIES.register("embedding")
class EmbeddingRanker:
    def rank(self, candidates: list[KBCandidate], query: Query) -> list[KBCandidate]:
        ...
```

It immediately shows up in `GET /kbits/strategies` and is selectable via
`rank_strategy: "embedding"`. No orchestrator or endpoint changes needed. This is
how embedding-based screening/ranking and a real web-search source drop in later.

## Testing

Tests live in `backend/tests/test_kbits.py`. External dependencies are mocked at
their **import site** in each submodule, e.g.:

- `api.v1.kbits_api.pipeline.sources.litellm` (LLM source)
- `api.v1.kbits_api.pipeline.orchestrator.get_supabase_service_client`
- `api.v1.kbits_api.access.get_supabase_service_client`

Run:

```bash
cd backend && python -m pytest tests/test_kbits.py -q
```
