-- Per-user Google Workspace (Calendar + Tasks) OAuth connections.
--
-- One row per user who has connected their Google account. Refresh tokens are
-- encrypted at rest by the backend (Fernet) before being written here, and are
-- never exposed to the frontend: only the service role reads/writes this table.
-- The frontend may read its own row (RLS) to show connection status, but the
-- token columns should never be selected client-side.
create table public.google_connections (
  user_id uuid primary key references auth.users (id) on delete cascade,
  google_email text,
  refresh_token_enc text not null,
  access_token text,
  token_expiry timestamptz,
  scopes text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.set_google_connections_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger google_connections_set_updated_at
  before update on public.google_connections
  for each row
  execute function public.set_google_connections_updated_at();

alter table public.google_connections enable row level security;

-- Users may read their own connection row (to render "Connected as ...").
-- Inserts/updates/deletes happen server-side with the service role key, which
-- bypasses RLS, so no write policies are defined here.
create policy "Users can view their own google connection"
  on public.google_connections
  for select
  using (auth.uid() = user_id);
