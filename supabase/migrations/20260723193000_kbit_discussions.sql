-- Let a knowledge bit host a discussion thread by reusing the existing chat
-- machinery. A discussion is just a normal conversation (ADK session + metadata
-- row) that carries a reference to its knowledge bit.
--
-- The bit itself is never stored as a chat message: it is injected into the
-- agent's system prompt at request time (see agent._instruction_provider), so
-- the agent always grounds its replies in the live bit regardless of how deep
-- the thread gets.
alter table public.conversations
  add column kbit_id uuid references public.knowledge_bits (id) on delete cascade;

-- At most one discussion conversation per knowledge bit. The partial index only
-- covers kbit-linked rows, so ordinary chats (kbit_id is null) are unaffected.
create unique index conversations_kbit_id_key
  on public.conversations (kbit_id)
  where kbit_id is not null;
