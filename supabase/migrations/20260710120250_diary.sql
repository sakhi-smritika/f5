create table public.diary (
  id uuid primary key default gen_random_uuid(),
  "date" date not null,
  general_content text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  user_id uuid not null references auth.users (id) on delete cascade,
  constraint diary_user_id_date_key unique (user_id, "date")
);

create or replace function public.set_diary_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger diary_set_updated_at
  before update on public.diary
  for each row
  execute function public.set_diary_updated_at();

alter table public.diary enable row level security;

create policy "Users can view their own diary entries"
  on public.diary
  for select
  using (auth.uid() = user_id);

create policy "Users can insert their own diary entries"
  on public.diary
  for insert
  with check (auth.uid() = user_id);

create policy "Users can update their own diary entries"
  on public.diary
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can delete their own diary entries"
  on public.diary
  for delete
  using (auth.uid() = user_id);
