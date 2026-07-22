# Chat API

FastAPI routes for Sakhi Smritika's chat feature. Conversations are backed by the
ADK agent: message content lives in ADK session tables, while sidebar metadata
(title, folders, timestamps) lives in `public.conversations`.

Mounted at `/api/v1/chat` via `api/v1/router.py`.

## Layout

```
chat_api/
├── README.md
├── __init__.py          # exports `router`
├── router.py            # composes sub-routers (no business logic)
├── schemas.py           # Pydantic request bodies
├── constants.py         # shared constants (e.g. DEFAULT_TITLE)
├── access.py            # ownership checks + read-only Supabase queries
├── utils.py             # pure helpers (SSE framing, title derivation, errors)
├── conversations.py     # create / update / delete conversations
├── messages.py          # load history + SSE streaming
├── attachments.py       # upload / delete files + link to ADK events
└── folders.py           # delete folder (cascades through conversation cleanup)
```

## File responsibilities

| File | What belongs here |
|------|-------------------|
| `router.py` | `include_router` only. No handlers, no DB calls. |
| `schemas.py` | Request/response Pydantic models. |
| `constants.py` | Module-level constants shared across handlers. |
| `access.py` | `get_owned_conversation`, `get_owned_folder`, attachment lookups. Raises `404` when the user does not own the resource. |
| `utils.py` | Stateless helpers with no I/O (SSE strings, title trimming, client clock labels). |
| `conversations.py` | Conversation CRUD routes and shared delete/persist helpers used by other modules. |
| `messages.py` | ADK session reads, `send_message` SSE stream, runner integration. |
| `attachments.py` | Supabase Storage upload/delete and pending-attachment rows. |
| `folders.py` | Folder delete; reuses `delete_conversation_fully` from `conversations.py`. |

## Endpoints

| Method | Path | Module |
|--------|------|--------|
| `POST` | `/conversations` | `conversations.py` |
| `PATCH` | `/conversations/{id}` | `conversations.py` |
| `DELETE` | `/conversations/{id}` | `conversations.py` |
| `GET` | `/conversations/{id}/messages` | `messages.py` |
| `POST` | `/conversations/{id}/messages` | `messages.py` |
| `POST` | `/conversations/{id}/attachments` | `attachments.py` |
| `DELETE` | `/conversations/{id}/attachments/{aid}` | `attachments.py` |
| `DELETE` | `/folders/{id}` | `folders.py` |

The frontend reads the conversation list directly from Supabase (RLS). All writes
to `conversations` and `chat_folder` go through these endpoints using the service
role client.

## Adding a new endpoint

1. Pick the domain file (or create a new one if it is a new area).
2. Add request/response models to `schemas.py` if needed.
3. Put ownership checks and Supabase reads in `access.py`.
4. Register the route on that file's `router`.
5. If it is a new file, `include_router` it in `router.py`.
6. Add tests in `backend/tests/test_chat.py`.

Keep route handlers thin: validate input, call helpers, return a response.

## Cross-module dependencies

```
router.py
  ├── conversations.py  → access, utils, agent, supabase
  ├── messages.py       → access, attachments, conversations, utils, agent
  ├── attachments.py    → access, chat_attachments, supabase
  └── folders.py        → access, conversations, supabase
```

Shared delete logic lives in `conversations.py` (`delete_conversation_fully`) so
folder delete and single-conversation delete stay consistent (ADK session, storage
objects, metadata row).

## Testing

Tests live in `backend/tests/test_chat.py`. Dependencies are mocked at their
**import site** in each submodule, for example:

- `api.v1.chat_api.conversations.get_session_service`
- `api.v1.chat_api.messages.get_runner`
- `api.v1.chat_api.access.get_supabase_service_client`
- `api.v1.chat_api.attachments.upload_to_storage`

Patch where the name is bound in the module under test, not where it is defined.

Run:

```bash
cd backend && python -m pytest tests/test_chat.py -q
```

## When to split further

Consider a `services/` or `repository.py` layer if:

- A route handler grows beyond ~40 lines of business logic
- Multiple modules need the same multi-step Supabase workflow
- Streaming logic in `messages.py` needs its own test surface

Until then, the current flat layout keeps navigation simple.
