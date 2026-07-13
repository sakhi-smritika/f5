create table public.goals (
  id uuid primary key default gen_random_uuid(),
  goal_name text not null,
  goal_description text,
  progress text,
  parent_goal uuid references public.goals (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index goals_user_id_idx on public.goals (user_id);
create index goals_parent_goal_idx on public.goals (parent_goal);

create or replace function public.set_goals_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger goals_set_updated_at
  before update on public.goals
  for each row
  execute function public.set_goals_updated_at();

alter table public.goals enable row level security;

create policy "Users can view their own goals"
  on public.goals
  for select
  using (auth.uid() = user_id);

create policy "Users can insert their own goals"
  on public.goals
  for insert
  with check (auth.uid() = user_id);

create policy "Users can update their own goals"
  on public.goals
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can delete their own goals"
  on public.goals
  for delete
  using (auth.uid() = user_id);
