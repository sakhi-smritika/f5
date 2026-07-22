-- Automatically enable Row Level Security on every table created in the
-- `public` schema.
--
-- Motivation: some tables are created at runtime outside of migrations (e.g.
-- Google ADK's DatabaseSessionService auto-creates `sessions`, `events`,
-- `app_states`, `user_states`). Because `public` is exposed via PostgREST and
-- new tables inherit broad grants, any table created without RLS is readable by
-- the `anon`/`authenticated` API roles. This migration guarantees RLS is turned
-- on for such tables even when we forget (or never run) an explicit migration.
--
-- Important: enabling RLS *without* policies denies access to the API roles
-- (`anon`, `authenticated`) but the table OWNER and `service_role` still bypass
-- RLS. We intentionally do NOT use FORCE ROW LEVEL SECURITY, so the backend
-- (service role) and ADK (table owner) keep working, while direct client access
-- through PostgREST is blocked until explicit policies are added.

-- 1. Event-trigger function: runs after any DDL and enables RLS on newly
--    created ordinary/partitioned tables in the `public` schema.
create or replace function public.auto_enable_rls()
returns event_trigger
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
  obj record;
begin
  for obj in
    select *
    from pg_event_trigger_ddl_commands()
    where command_tag = 'CREATE TABLE'
      and schema_name = 'public'
      and object_type = 'table'
  loop
    execute format(
      'alter table %s enable row level security',
      obj.object_identity
    );
  end loop;
end;
$$;

comment on function public.auto_enable_rls() is
  'Enables RLS on any table created in the public schema (see migration 20260723120000).';

-- 2. Register the event trigger (drop first so the migration is idempotent).
drop event trigger if exists auto_enable_rls_on_create;

create event trigger auto_enable_rls_on_create
  on ddl_command_end
  when tag in ('CREATE TABLE')
  execute function public.auto_enable_rls();

-- 3. One-time backfill: enable RLS on existing public tables that don't have it
--    yet. Tables that already have RLS (all current app tables) are skipped, so
--    their existing policies are untouched. This closes the gap for any ADK
--    session tables that were already created before this migration ran.
do $$
declare
  r record;
begin
  for r in
    select c.oid::regclass as tbl
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relkind in ('r', 'p')      -- ordinary + partitioned tables
      and not c.relrowsecurity          -- skip tables that already have RLS
  loop
    execute format('alter table %s enable row level security', r.tbl);
  end loop;
end;
$$;
