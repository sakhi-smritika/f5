-- Chat file attachments (uploaded before send, linked to ADK event on send).

create table public.chat_attachments (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null
    references public.conversations (id) on delete cascade,
  user_id uuid not null
    references auth.users (id) on delete cascade,
  storage_path text not null,
  filename text not null,
  mime_type text not null,
  size_bytes bigint not null,
  adk_event_id text,
  created_at timestamptz not null default now()
);

create index chat_attachments_conversation_id_idx
  on public.chat_attachments (conversation_id);

create index chat_attachments_adk_event_id_idx
  on public.chat_attachments (adk_event_id)
  where adk_event_id is not null;

create index chat_attachments_pending_idx
  on public.chat_attachments (conversation_id, created_at)
  where adk_event_id is null;

alter table public.chat_attachments enable row level security;

create policy "Users can view their own chat attachments"
  on public.chat_attachments
  for select
  using (auth.uid() = user_id);

-- Private bucket for chat uploads. All access goes through the backend (service role).
insert into storage.buckets (id, name, public, file_size_limit)
values ('chat-attachments', 'chat-attachments', false, 10485760)
on conflict (id) do nothing;
