alter table public.diary
  add column if not exists how_was_the_day text,
  add column if not exists major_events text;
