create table if not exists public.knowledge_bits (
    -- meta data about the kb
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),  
    updated_at timestamptz not null default now(),
    user_id uuid not null references auth.users (id) on delete cascade,

    -- actual content of the kb
    title text not null,
    content text not null,

    -- parameters on kb for helping screen, rank and query
    related_goal uuid references public.goals(id), -- kept nullable to promote goalless KBs
    is_read boolean not null default false,
    is_liked boolean not null default false,
    is_disliked boolean not null default false,
    rating integer,
    is_marked_irrelavant boolean not null default false,
    is_marked_relavant boolean not null default false
);

create or replace function public.set_kb_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create or replace trigger kb_set_updated_at
  before update on public.knowledge_bits
  for each row
  execute function public.set_kb_updated_at();

alter table public.knowledge_bits enable row level security;

drop policy if exists "Users can view their own kb entries"
on public.knowledge_bits;
create  policy "Users can view their own kb entries"
  on public.knowledge_bits
  for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert their own kb entries"
on public.knowledge_bits;
create policy "Users can insert their own kb entries"
  on public.knowledge_bits
  for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can update their own kb entries"
on public.knowledge_bits;
create policy "Users can update their own kb entries"
  on public.knowledge_bits
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can delete their own kb entries"
on public.knowledge_bits;
create policy "Users can delete their own kb entries"
  on public.knowledge_bits
  for delete
  using (auth.uid() = user_id);
