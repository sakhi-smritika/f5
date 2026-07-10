# Backend

FastAPI service for the personal-growth app. It handles logic that shouldn't run in the browser and validates requests against Supabase Auth. Simple CRUD is currently done directly from the frontend via Supabase, so this service is intentionally small and is where server-side features are added over time.

## Stack

- **FastAPI** + **uvicorn**
- **supabase** (Python client) for verifying bearer tokens
- **python-json-logger** for structured logging
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
| `SUPABASE_SECRET_KEY` | Supabase service-role key (for privileged operations) |
| `ENVIRONMENT` | `local` or `production` (controls CORS policy) |

## Project structure

```
main.py                 # Entry point: app = create_app(); runs uvicorn on :8080
app.py                  # create_app(): CORS, middleware, routers, health + error handlers
api/
  v1/
    router.py           # /api/v1 router (all routes require auth); sample GET /hello
config/
  supabase.py           # get_supabase_client() (cached) from SUPABASE_URL/PUBLISHABLE_KEY
  auth.py               # get_current_user() dependency + AuthenticatedUser
  middleware.py         # RequestLoggingMiddleware (per-request structured logs)
  logger.py             # setup_logging(): colored console + JSON file logs in logs/
tests/
  conftest.py           # fixtures: app, client, unauthenticated_client, auth override
  test_app.py           # app creation, /health, /api/v1/hello (+ auth) , 500 handler
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

## Logging

`setup_logging()` (called in `create_app`) configures the root logger with a colored console handler and a JSON file handler that writes a timestamped file into `backend/logs/`. Attach structured context with the `extra=` kwarg, e.g. `logger.info("...", extra={"user_id": user.id})`. Noisy third-party loggers and `uvicorn.access` are turned down.

## Adding a new endpoint

Add a route in `api/v1/router.py` (the router already applies `get_current_user` as a dependency, so it's authenticated by default), inject `user: AuthenticatedUser = Depends(get_current_user)` when you need the caller, and add a test in `tests/`.
