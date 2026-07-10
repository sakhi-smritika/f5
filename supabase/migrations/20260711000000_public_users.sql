create table public.users (
  id uuid primary key references auth.users (id) on delete cascade,
  username text unique,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.set_public_users_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger users_set_updated_at
  before update on public.users
  for each row
  execute function public.set_public_users_updated_at();

alter table public.users enable row level security;

create policy "Users can view their own profile"
  on public.users
  for select
  using (auth.uid() = id);

create policy "Users can insert their own profile"
  on public.users
  for insert
  with check (auth.uid() = id);

create policy "Users can update their own profile"
  on public.users
  for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- Auto-provision a profile row whenever a new auth user is created.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id)
  values (new.id)
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row
  execute function public.handle_new_user();

-- Backfill profile rows for users that already exist.
insert into public.users (id)
select id from auth.users
on conflict (id) do nothing;
