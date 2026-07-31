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
    ├── query.py         # QUERY_STRATEGIES  (default: goals_profile; agent)
    ├── generators.py    # GENERATOR_STRATEGIES (default: llm)
    ├── screener.py      # SCREEN_STRATEGIES (default: text)
    ├── ranker.py        # RANK_STRATEGIES   (default: text)
    └── orchestrator.py  # resolve strategies -> build -> generate -> screen -> rank -> insert
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
  "generator_strategy": "llm",
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
fixed input/output contract. `invoke` is simply the point where the backend
learns that bits are wanted; the stages do the rest.

```
build(Query) -> generate -> screen -> rank -> insert
```

The **query** stage decides *what kind* of bits this user needs right now. The
**generate** stage produces them. Screening and ranking then trim and order the
candidates before the top few are inserted.

Contracts (see `pipeline/base.py`):

| Stage | Protocol | Signature |
|-------|----------|-----------|
| query | `QueryStrategy` | `async build(ctx) -> Query` |
| generate | `GeneratorStrategy` | `async generate(query, limit) -> list[KBCandidate]` |
| screen | `ScreenStrategy` | `screen(candidates, ctx) -> list[KBCandidate]` |
| rank | `RankStrategy` | `rank(candidates, query) -> list[KBCandidate]` |

Each stage module owns a `Registry` and registers strategies by name, marking
one as the default.

Query and generate are awaited because they call agents and models; screen and
rank are in-process transforms. `invoke_kbits` sets `current_user_id` around both
awaited stages so agent tools scope their reads to the signed-in user.

`PipelineContext` preloads goals, profile and existing bit titles for the
strategies that want them. Agent-backed strategies ignore it and read live data
through tools instead.

### Query strategies

| Name | What it does |
|------|--------------|
| `goals_profile` (default) | Include terms from every goal + profile background; exclude recent bit titles |
| `single_goal` | Same, narrowed to `goal_id` (falls back to `goals_profile` without one) |
| `agent` | An agent reads goals, diary, calendar, tasks and past bits with read-only tools, then submits the query |

The `agent` strategy reports its answer by calling a `submit_kbit_query` tool
(see `agent/kbit_query_agent.py`), so the tool's arguments *are* the structured
output. That avoids ADK's `output_schema`, which is enforced unreliably once an
agent has tools of its own. It fills `Query.brief` with prose the term lists
cannot carry, and recent bit titles are merged into `exclude` regardless, so
dedup never depends on the agent remembering them. If the agent submits nothing,
the strategy falls back to `goals_profile` rather than failing the invoke.

### Generator strategies

| Name | What it does |
|------|--------------|
| `llm` (default) | One LiteLLM call that writes bits from `Query.to_text()` |

### Adding a strategy

```python
from .base import KBCandidate, Query, Registry
from .ranker import RANK_STRATEGIES

@RANK_STRATEGIES.register("embedding")
class EmbeddingRanker:
    def rank(self, candidates: list[KBCandidate], query: Query) -> list[KBCandidate]:
        ...
```

Query and generator strategies are the exception: define their method as
`async def`.

It immediately shows up in `GET /kbits/strategies` and is selectable via
`rank_strategy: "embedding"`. No orchestrator or endpoint changes needed. This is
how embedding-based screening/ranking and a web-grounded generator drop in later.

## Testing

Tests live in `backend/tests/test_kbits.py`. External dependencies are mocked at
their **import site** in each submodule, e.g.:

- `api.v1.kbits_api.pipeline.generators.litellm` (generators await `acompletion`)
- `api.v1.kbits_api.pipeline.query.build_kbit_query` (the query agent)
- `api.v1.kbits_api.pipeline.orchestrator.get_supabase_service_client`
- `api.v1.kbits_api.access.get_supabase_service_client`

Run:

```bash
cd backend && python -m pytest tests/test_kbits.py -q
```
