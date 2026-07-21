# Framework 5

A personal-growth app. 

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

## Quick start the development environment

```bash

# 1. Clone the repo
git clone https://github.com/sakhi-smritika/f5.git

# 2. Install Supabase CLI (https://supabase.com/docs/guides/cli)
brew install supabase/tap/supabase

# 3. Start Supabase locally (http://localhost:54321)
# Docker is a prerequisite; see https://supabase.com/docs/guides/cli#docker
cd supabase && supabase start

# Note the Supabase project URL, Publishable and Secret Keys from the output of supabase start. You'll need them for the frontend and backend .env files.

# 4. Start the backend locally (http://localhost:8080)
# Python 3.13 is a prerequisite; see https://www.python.org/downloads/

# Go to the backend Folder
cd backend
# Create Virtual Environment
python -m venv venv 
# Activate the Virtual Environment
source venv/bin/activate
# Install the dependencies along with dev dependencies
pip install -r requirements-dev.txt
# Copy the .env.example to .env and fill variables. Refer to backend/README.md for details.
cp .env.example .env
# Run the backend server
uvicorn main:app --port=8080

# 5. Start the frontend locally (http://localhost:5173)
# Node.js is a prerequisite; see https://nodejs.org/en/download/

# Go to the frontend Folder
cd frontend
# Install the dependencies
npm install
# Copy the .env.example to .env and fill variables. Refer to frontend/README.md for details.
cp .env.example .env
# Run the frontend server
npm run dev




Each subproject has its own `.env.example` — copy and fill it in before running. See the per-directory READMEs for details on environment variables, structure, and conventions.
