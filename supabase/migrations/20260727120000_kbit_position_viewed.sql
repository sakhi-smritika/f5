-- Add feed ordering and viewed tracking for knowledge bits.

alter table public.knowledge_bits
  add column if not exists position integer,
  add column if not exists is_viewed boolean not null default false;

-- Backfill position per user in creation order (oldest = 1).
with ranked as (
  select
    id,
    row_number() over (
      partition by user_id
      order by created_at asc, id asc
    ) as pos
  from public.knowledge_bits
)
update public.knowledge_bits kb
set position = ranked.pos
from ranked
where kb.id = ranked.id
  and kb.position is null;

-- Treat previously read bits as already viewed so they stay out of the feed.
update public.knowledge_bits
set is_viewed = true
where is_read = true
  and is_viewed = false;

alter table public.knowledge_bits
  alter column position set not null;

create or replace function public.set_kb_position()
returns trigger
language plpgsql
as $$
begin
  if new.position is null then
    select coalesce(max(position), 0) + 1
    into new.position
    from public.knowledge_bits
    where user_id = new.user_id;
  end if;
  return new;
end;
$$;

drop trigger if exists kb_set_position on public.knowledge_bits;
create trigger kb_set_position
  before insert on public.knowledge_bits
  for each row
  execute function public.set_kb_position();

create index if not exists knowledge_bits_user_feed_idx
  on public.knowledge_bits (user_id, is_viewed, position);
