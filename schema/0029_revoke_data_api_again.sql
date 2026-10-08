-- 0029. Revoke the Neon Data API roles again, on 8 October 2026.
--
-- On 8 October 2026 the Neon Data API was found active on production again
-- (branch br-plain-sea-zaphlsmw, database myshopedge, status "active", serving
-- schema public with anonymous as the anonymous role). It had re-created what
-- 0024 removed on 24 September: default privileges on mse_migrator granting
-- authenticated every right on new tables, sequences and functions; SELECT,
-- INSERT, UPDATE and DELETE for authenticated on 42 tables in public; and
-- EXECUTE for authenticated on all nine SECURITY DEFINER functions. Development
-- and staging held none of it. Nobody has established when or how it was
-- switched on.
--
-- It was found because 0028's closing check refused to apply on production:
-- the new table was granted to authenticated the moment it was created.
--
-- The owner approved deleting the production Data API the same day, and it was
-- deleted through Neon's API (DELETE .../branches/br-plain-sea-zaphlsmw/
-- data-api/myshopedge, then GET answered "data api not found"). This migration
-- then revokes exactly what 0024 revoked, by the same statements, and ends with
-- 0024's closing check, so it raises if either role still holds a table right,
-- can call a SECURITY DEFINER function, or is granted anything by default.
--
-- On a branch where the roles hold nothing (development, staging), every
-- statement is a no-op and the check passes.
--
-- ORDER ON PRODUCTION: 0029 is applied before 0028 there, because 0028's own
-- check cannot pass until these grants are gone. migrate.py applies whatever is
-- pending, so the order of the files does not stop this.

do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anonymous'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      execute format('revoke all on all tables in schema public from %I', r);
      execute format('revoke all on all sequences in schema public from %I', r);
      execute format('revoke all on all functions in schema public from %I', r);
      execute format(
        'alter default privileges for role mse_migrator in schema public revoke all on tables from %I', r);
      execute format(
        'alter default privileges for role mse_migrator in schema public revoke all on sequences from %I', r);
      execute format(
        'alter default privileges for role mse_migrator in schema public revoke all on functions from %I', r);
    end if;
  end loop;
end $$;


do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anonymous'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      if exists (
        select 1 from information_schema.role_table_grants
         where table_schema = 'public' and grantee = r
      ) then
        raise exception 'role % still holds a right on a table in public', r;
      end if;
      if exists (
        select 1 from pg_proc p join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public' and p.prosecdef
           and has_function_privilege(r, p.oid, 'EXECUTE')
      ) then
        raise exception 'role % can still call a SECURITY DEFINER function in public', r;
      end if;
      if exists (
        select 1 from pg_default_acl d
         where d.defaclrole = 'mse_migrator'::regrole
           and d.defaclacl::text like '%' || r || '=%'
      ) then
        raise exception 'mse_migrator still grants % by default', r;
      end if;
    end if;
  end loop;
end $$;
