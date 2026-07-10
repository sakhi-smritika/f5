# Supabase

Database schema, migrations, and seed scripts for the personal-growth app. Supabase provides **auth**, the **Postgres database**, and the **data API** that the frontend uses directly. Access control is enforced with Row Level Security (RLS), so every table scopes rows to the signed-in user.

## Layout

```
config.toml                 # Supabase CLI project config (local dev + push behavior)
migrations/                 # SQL migrations, applied in filename (timestamp) order
  20260710113050_remote_schema.sql   # Baseline: extensions, schema grants, default privileges
  20260710120250_diary.sql           # `diary` table (diary text + hourly day_log) + RLS
  20260711000000_public_users.sql    # `users` profile table + signup trigger + RLS
seed.py                     # Runner: executes python_seeds/*.py in numeric order
python_seeds/
  001_seed_users.py         # Creates auth users via the Admin API (needs secret key)
.env.example                # SUPABASE_URL / PUBLISHABLE_KEY / SECRET_KEY
```

## Schema overview

### `public.diary`
One row per user per date. Stores both the free-text diary and the hourly day log.

- `id uuid pk`, `user_id uuid -> auth.users` (cascade delete)
- `date date`, unique together with `user_id` (`diary_user_id_date_key`) — enables upserts
- `general_content text` — the Diary page's free text
- `day_log jsonb` (default `{}`) — Day Log page's 24 hourly slots, keyed `"0"`..`"23"`
- `created_at`, `updated_at` (auto-updated via `set_diary_updated_at` trigger)
- RLS: users can select/insert/update/delete only their own rows.

### `public.users` (profiles)
Per-user profile, keyed by the auth user id.

- `id uuid pk -> auth.users` (cascade delete)
- `username text unique`, `display_name text`
- `created_at`, `updated_at` (auto-updated via `set_public_users_updated_at` trigger)
- RLS: users can select/insert/update only their own row.
- A row is auto-created on signup by the `handle_new_user` trigger on `auth.users`; the migration also backfills existing users. `display_name` starts `NULL`, so the frontend falls back to email until it's set.

## Common workflows

Run these from the `supabase/` directory (CLI must be linked to the project).

```bash
# Push new migrations to the linked remote database
supabase db push

# Reset the LOCAL database: drop, re-run all migrations, then SQL seeds (destructive)
supabase db reset

# Run Python seeds (creates auth users). Do this AFTER migrations/reset.
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py
```

### Adding a migration
Create a new timestamped file in `migrations/` (`YYYYMMDDHHMMSS_name.sql`). Follow the existing style: create the table, add an `updated_at` trigger, `enable row level security`, then per-operation policies keyed on `auth.uid()`.

use 
```bash
supabase migration new name
```
to create a new migration file.

## Environment variables

Copy `.env.example` to `.env` for the seed scripts:

- `SUPABASE_URL` — project URL
- `SUPABASE_PUBLISHABLE_KEY` — publishable (anon) key
- `SUPABASE_SECRET_KEY` — service-role key (required by `python_seeds` admin operations; find via `supabase status`)
