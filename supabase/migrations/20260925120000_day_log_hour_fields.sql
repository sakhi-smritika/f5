-- Rewrite day_log hour values from a single string to {done, impact}.
-- Existing text becomes `done`; `impact` starts empty. Object values are normalized.

update public.diary
set day_log = coalesce((
  select jsonb_object_agg(
    slot.key,
    case
      when jsonb_typeof(slot.value) = 'string' then
        jsonb_build_object('done', slot.value #>> '{}', 'impact', '')
      when jsonb_typeof(slot.value) = 'object' then
        jsonb_build_object(
          'done', coalesce(slot.value ->> 'done', ''),
          'impact', coalesce(slot.value ->> 'impact', '')
        )
      else
        jsonb_build_object('done', '', 'impact', '')
    end
  )
  from jsonb_each(
    case
      when jsonb_typeof(day_log) = 'object' then day_log
      else '{}'::jsonb
    end
  ) as slot
), '{}'::jsonb);

comment on column public.diary.day_log is
  'Hourly slots keyed "0".."23". Each value is {"done": text, "impact": text}.';
