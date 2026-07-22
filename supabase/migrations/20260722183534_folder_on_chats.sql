-- Create chat_folder table to organize conversations by folders
create table public.chat_folder (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index chat_folder_user_id_idx on public.chat_folder (user_id);

-- Trigger to update updated_at timestamp
create or replace function public.set_chat_folder_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger chat_folder_set_updated_at
  before update on public.chat_folder
  for each row
  execute function public.set_chat_folder_updated_at();

-- Add folder_id to conversations table
alter table public.conversations
add column folder_id uuid references public.chat_folder (id) on delete cascade;

create index conversations_folder_id_idx on public.conversations (folder_id);

-- Update the conversations index to include folder_id for efficient sidebar queries
create index conversations_user_folder_updated_at_idx
  on public.conversations (user_id, folder_id, updated_at desc);

-- Enable RLS on chat_folder
alter table public.chat_folder enable row level security;

-- RLS policy: users can view their own folders
create policy "Users can view their own folders"
  on public.chat_folder
  for select
  using (auth.uid() = user_id);

-- RLS policy: users can insert folders
create policy "Users can create folders"
  on public.chat_folder
  for insert
  with check (auth.uid() = user_id);

-- RLS policy: users can update their own folders
create policy "Users can update their own folders"
  on public.chat_folder
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- RLS policy: users can delete their own folders
create policy "Users can delete their own folders"
  on public.chat_folder
  for delete
  using (auth.uid() = user_id);
