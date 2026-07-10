# Framework 5

A personal-growth app. The current focus is an **Introspection** area with a **Diary** (free-text per day) and a **Day Log** (24 hourly slots per day).

## Architecture

```
Browser (React SPA)  --auth + CRUD-->  Supabase (Auth + Postgres + Data API)
        |
        \--(bearer token)-->  FastAPI backend (server-side logic)
```

- **Auth** is Supabase. The frontend signs in with email/password and receives a session/JWT.
- **Simple CRUD** goes straight from the frontend to Supabase's data API; **Row Level Security** scopes every row to the signed-in user.
- **The backend** validates the same Supabase bearer token and hosts logic that shouldn't live in the client. It's small today and grows as needed.

## Repository layout

| Directory | What it is | README |
| --- | --- | --- |
| `frontend/` | React + TypeScript + Vite SPA (deployed on Vercel) | [frontend/README.md](frontend/README.md) |
| `backend/` | FastAPI service (Python) | [backend/README.md](backend/README.md) |
| `supabase/` | DB schema, migrations, and seed scripts | [supabase/README.md](supabase/README.md) |

## Quick start

```bash
# 1. Database: push migrations to your linked Supabase project
cd supabase && supabase db push

# 2. Backend (http://localhost:8080)
cd backend && python -m venv .venv && source .venv/bin/activate \
  && pip install -r requirements.txt && python main.py

# 3. Frontend (http://localhost:5173)
cd frontend && npm install && npm run dev
```

Each subproject has its own `.env.example` — copy and fill it in before running. See the per-directory READMEs for details on environment variables, structure, and conventions.
