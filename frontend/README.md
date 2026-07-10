# Frontend

React + TypeScript + Vite single-page app. It is the user-facing part of the personal-growth app, and talks to **Supabase directly** for auth and simple CRUD. A separate FastAPI backend (`../backend`) exists for logic that shouldn't live in the client, but most current pages use Supabase's data API straight from the browser (RLS enforces per-user access).

## Stack

- **React 19** + **TypeScript**, bundled with **Vite**
- **react-router-dom** for routing
- **@supabase/supabase-js** for auth + data
- ESLint (with the React Compiler lint rules, hence some strict `react-hooks/*` rules)

## Getting started

```bash
npm install
npm run dev      # start Vite dev server (http://localhost:5173)
npm run build    # tsc -b && vite build -> dist/
npm run lint     # eslint
npm run preview  # preview a production build
```

## Environment variables

Vite only exposes vars prefixed with `VITE_`. Copy `.env.example` to `.env.local` (dev) / `.env.production` (build) and fill in:

| Variable | Purpose |
| --- | --- |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable (anon) key |
| `VITE_BACKEND_URL` | Base URL of the FastAPI backend (used by `apiFetch`; blank = same origin / Vite proxy) |

In dev, `vite.config.ts` proxies `/api` to `BACKEND_URL` (default `http://localhost:8080`).

## Project structure

```
src/
  main.tsx              # App bootstrap: wraps <App/> in <AuthProvider/>
  App.tsx               # Route table (see Routing below)
  context/
    AuthContext.tsx     # useAuth(): session, user, signIn, signOut (Supabase auth)
  components/
    ProtectedRoute.tsx  # Guards routes; also PublicRoute for the login page
    Layout.tsx          # Persistent top header + pane-selector nav + <Outlet/>
  pages/
    LoginPage.tsx       # Email/password sign-in
    DiaryPage.tsx       # Introspection > Diary (free-text entry per date)
    DayLogPage.tsx      # Introspection > Day Log (24 hourly slots per date)
    HomePage.tsx        # Legacy starter page, currently not routed
  lib/
    supabase.ts         # Configured Supabase client (singleton)
    api.ts              # apiFetch(): fetch wrapper that attaches the Supabase bearer token
    diary.ts            # Data access for the `diary` table (diary text + day_log jsonb)
    profile.ts          # Data access for the `users` (profile) table
```

## Routing

Defined in `src/App.tsx`:

- `/login` — public (redirects to `/` if already signed in)
- Everything else is wrapped in `ProtectedRoute` -> `Layout`:
  - `/introspection/diary` — Diary pane
  - `/introspection/day-log` — Day Log pane
  - `/` — redirects to `/introspection/diary`

New panes are added by (1) adding an item to `paneCategories` in `Layout.tsx` and (2) adding a `<Route>` in `App.tsx`.

## Auth

`AuthContext` initializes from `supabase.auth.getSession()` and subscribes to `onAuthStateChange`. `ProtectedRoute` waits for `loading` then redirects to `/login` when there's no session. `Layout` shows the user's `display_name` (from the `users` table) and falls back to their email.

## Data access

Pages call the Supabase client directly through small helpers in `src/lib/`. Row Level Security on the Supabase side scopes every row to the signed-in user, so the client only ever filters by things like `date`. Writes use `upsert(..., { onConflict: 'user_id,date' })` against the `diary` table's unique constraint.

For calls that go through the backend instead, use `apiFetch(path)` from `src/lib/api.ts` — it injects the `Authorization: Bearer <access_token>` header and signs the user out on a `401`.

## Deployment (Vercel)

The Vercel project's **Root Directory is `frontend/`**. `frontend/vercel.json` rewrites all paths to `/index.html` so client-side deep links (e.g. refreshing `/introspection/day-log`) don't 404. If you change the Vercel root directory, move `vercel.json` accordingly.
