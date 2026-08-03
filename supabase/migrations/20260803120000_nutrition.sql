alter table public.diary
  add column if not exists nutrition_entries jsonb not null default '[]'::jsonb;

create table public.nutrition_templates (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  hour int not null check (hour >= 0 and hour <= 23),
  nutrition text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index nutrition_templates_user_id_idx on public.nutrition_templates (user_id);
create index nutrition_templates_user_active_idx on public.nutrition_templates (user_id, is_active);

create or replace function public.set_nutrition_templates_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger nutrition_templates_set_updated_at
  before update on public.nutrition_templates
  for each row
  execute function public.set_nutrition_templates_updated_at();

alter table public.nutrition_templates enable row level security;

create policy "Users can view their own nutrition templates"
  on public.nutrition_templates
  for select
  using (auth.uid() = user_id);

create policy "Users can insert their own nutrition templates"
  on public.nutrition_templates
  for insert
  with check (auth.uid() = user_id);

create policy "Users can update their own nutrition templates"
  on public.nutrition_templates
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can delete their own nutrition templates"
  on public.nutrition_templates
  for delete
  using (auth.uid() = user_id);
