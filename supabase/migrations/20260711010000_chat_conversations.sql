-- Sidebar metadata for chat conversations. Message content itself lives in
-- ADK's own session tables (created at runtime by DatabaseSessionService); this
-- table only stores what the history list needs. `id` equals the ADK session id.
create table public.conversations (
  id uuid primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null default 'New chat',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index conversations_user_id_updated_at_idx
  on public.conversations (user_id, updated_at desc);

create or replace function public.set_conversations_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger conversations_set_updated_at
  before update on public.conversations
  for each row
  execute function public.set_conversations_updated_at();

alter table public.conversations enable row level security;

-- The frontend reads the sidebar list directly (RLS-scoped to the owner).
-- Inserts/updates/deletes are performed server-side with the service role key,
-- which bypasses RLS, so no write policies are defined here.
create policy "Users can view their own conversations"
  on public.conversations
  for select
  using (auth.uid() = user_id);
