-- Store the final user message sent to the LLM generator when a bit was created.
alter table public.knowledge_bits
  add column if not exists generator_prompt text;

comment on column public.knowledge_bits.generator_prompt is
  'User message sent to the LLM generator that produced this bit.';
