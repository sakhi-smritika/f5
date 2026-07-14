# Backend

FastAPI service for the personal-growth app. It handles logic that shouldn't run in the browser and validates requests against Supabase Auth. Simple CRUD is currently done directly from the frontend via Supabase, so this service is intentionally small and is where server-side features are added over time.

## Stack

- **Python 3.11.14**
- **FastAPI** + **uvicorn**
- **supabase** (Python client) for verifying bearer tokens
- **python-json-logger** for structured logging
- **google-adk** (`[db]` extra) + **litellm** for the chatbot agent; **asyncpg** for ADK session persistence
- **pytest** for tests

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# run the dev server (http://localhost:8080)
python main.py
# or: uvicorn main:app --reload --port 8080

# tests
pytest
```

## Environment variables

Copy `.env.example` to `.env`:

| Variable | Purpose |
| --- | --- |
| `LOGGING_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `CORS_ORIGINS` | Comma-separated allowed origins (local only) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase publishable (anon) key — used to validate user tokens |
| `SUPABASE_SECRET_KEY` | Supabase service-role key (privileged ops, e.g. `conversations` writes) |
| `OPENAI_API_KEY` | OpenAI key — used when a `CHAT_MODELS` entry starts with `openai/` |
| `GEMINI_API_KEY` | Google Gemini key — used when a model starts with `gemini/` |
| `ANTHROPIC_API_KEY` | Anthropic key — used when a model starts with `anthropic/` |
| `CHAT_MODELS` | Comma-separated LiteLLM model list for the chat UI (`id\|Label` or `id` only); first entry is the default |
| `DATABASE_URL` | Async SQLAlchemy URL for ADK session persistence, e.g. `postgresql+asyncpg://postgres:<pwd>@<host>:5432/postgres` (must use the `asyncpg` driver) |
| `ENVIRONMENT` | `local` or `production` (controls CORS policy) |

## Project structure

```
main.py                 # Entry point: app = create_app(); runs uvicorn on :8080
app.py                  # create_app(): CORS, middleware, routers, health + error handlers
api/
  v1/
    router.py           # /api/v1 router (all routes require auth); sample GET /hello; mounts chat
    chat.py             # /api/v1/chat endpoints (conversations, messages, SSE streaming)
agent/
  agent.py              # ADK LlmAgent (LiteLLM, multi-provider) + cached DatabaseSessionService & Runner
config/
  supabase.py           # get_supabase_client() + get_supabase_service_client() (service-role)
  auth.py               # get_current_user() dependency + AuthenticatedUser
  middleware.py         # RequestLoggingMiddleware (per-request structured logs)
  logger.py             # setup_logging(): colored console + JSON file logs in logs/
tests/
  conftest.py           # fixtures: app, client, unauthenticated_client, auth override
  test_app.py           # app creation, /health, /api/v1/hello (+ auth) , 500 handler
  test_chat.py          # chat endpoints (mocked ADK runner/session service + Supabase)
  test_middleware.py    # request logging middleware
  test_logger.py        # logging setup
```

## Request flow

1. `RequestLoggingMiddleware` times every request (skips `/health`) and logs method, path, status, duration, and client IP at info/warning/error depending on status code.
2. Routes under `api/v1/router.py` depend on `get_current_user`, which reads the `Authorization: Bearer <token>` header, calls `supabase.auth.get_user(token)`, and returns an `AuthenticatedUser(id, email, raw)`. Missing/invalid tokens -> `401`.
3. Unhandled exceptions are caught by a global handler that logs the exception and returns `500 {"detail": "Internal server error"}`.

## Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/health` | no | Liveness check -> `{"status": "ok"}` |
| GET | `/api/v1/hello` | yes | Sample endpoint -> `{"message": "hello", "user_id": ...}` |
| POST | `/api/v1/chat/conversations` | yes | Create a conversation (ADK session + metadata row) -> `{"id", "title"}` |
| GET | `/api/v1/chat/conversations/{id}/messages` | yes | Load a conversation's history -> `{"messages": [{"role", "text", "event_id", "attachments"}]}` |
| POST | `/api/v1/chat/conversations/{id}/messages` | yes | Send a message (optional `attachment_ids`); streams the reply as SSE (`data: {"delta"|"done"|"error"}`) |
| POST | `/api/v1/chat/conversations/{id}/attachments` | yes | Upload a file (multipart) before sending -> `{"id", "filename", "mime_type", "size_bytes", "url"}` |
| DELETE | `/api/v1/chat/conversations/{id}/attachments/{attachment_id}` | yes | Remove a not-yet-sent attachment -> `{"ok": true}` |
| DELETE | `/api/v1/chat/conversations/{id}` | yes | Delete a conversation (ADK session + metadata row + stored files) -> `{"ok": true}` |

## Chatbot (ADK)

The chat feature is powered by [Google ADK](https://adk.dev). `agent/agent.py` defines an `LlmAgent` backed by LiteLLM (OpenAI, Gemini, Anthropic), plus cached singletons for a `DatabaseSessionService` and a `Runner`.

- **Persistence (hybrid):** a conversation is an ADK *session*; its messages are ADK *events*, persisted by `DatabaseSessionService` in the Postgres database pointed at by `DATABASE_URL`. ADK auto-creates its own tables (`sessions`, `events`, `app_states`, `user_states`) on first use. A small `conversations` table (see `supabase/`) stores sidebar metadata (title, timestamps) for the history list.
- **Isolation:** every session is keyed by the authenticated Supabase `user_id`; ownership of `conversations` rows is checked on each request. Metadata writes use the service-role client (`get_supabase_service_client`).
- **Streaming:** `POST .../messages` runs the agent with `StreamingMode.SSE` and forwards partial text deltas to the browser as Server-Sent Events, followed by a terminal `{"done": true, "title": ...}` frame.
- **MCP servers:** add `McpToolset(...)` entries to the agent's `tools` list in `agent/agent.py` to connect Model Context Protocol servers (none are wired up yet).
- **File attachments:** files are uploaded before send to the private `chat-attachments` Supabase Storage bucket, tracked in the `chat_attachments` table, and linked to their ADK user event on send (`adk_event_id`). On send, the backend normalizes each file into GenAI `Part`s (`config/chat_attachments.py`, `agent/attachment_parts.py`): images and (for Gemini) PDFs are passed inline; other PDFs and text/code files are extracted to text so any provider can read them.

## Logging

`setup_logging()` (called in `create_app`) configures the root logger with a colored console handler and a JSON file handler that writes a timestamped file into `backend/logs/`. Attach structured context with the `extra=` kwarg, e.g. `logger.info("...", extra={"user_id": user.id})`. Noisy third-party loggers and `uvicorn.access` are turned down.

## Adding a new endpoint

Add a route in `api/v1/router.py` (the router already applies `get_current_user` as a dependency, so it's authenticated by default), inject `user: AuthenticatedUser = Depends(get_current_user)` when you need the caller, and add a test in `tests/`.
