-- 0030. The scheduled exports the daily job reads (MON-8, A5.7).
--
-- Written 9 October 2026, when scheduled exports were built with the owner's approval of
-- that day. **NOT APPLIED to any Neon branch.** Applied to local databases only. It goes on
-- with the owner's authority, as 0022 to 0029 did.
--
-- WHY A FUNCTION
--
-- `export_schedules` has existed since 0007, with row level security forced and a policy that
-- scopes it to the shops of `app_account_id()`. The daily job (`scripts/sync_shops.py`) runs
-- as `mse_app`, like every other part of the service, and so can see one account's schedules
-- at a time and cannot find the accounts that hold any. `export_schedules_due()` follows the
-- shape 0017, 0025, 0027 and 0028 set: SECURITY DEFINER, one statement, owned by
-- `mse_migrator`, executable by `mse_app` alone. It returns ids and nothing else. Each
-- schedule is then read, judged and built inside `tenant()`, under row level security.
--
-- The function does not decide which day a schedule falls due. That is a business rule, and
-- A29 puts every business rule in Python (`app/export_schedules.py`). It lists every active
-- schedule of an active account whose shop is not deleted. A closing or erased account is
-- left out, because A30.1 stops new data arriving once a deletion is requested, and the sync
-- job leaves such an account out for the same reason (0027).
--
-- THE INDEX
--
-- Every read the screen makes is by shop, and 0007 gave the table no index but its key.
--
-- No column is added. The table already holds what MON-8 needs: the kind, the format, the
-- basis, the cadence, the day and `last_run_at`. The account is reached through the shop,
-- and the day is judged in Europe/London by the code, as every other date in the service is.

create index if not exists export_schedules_shop_idx on export_schedules (shop_id, created_at);

create or replace function export_schedules_due()
  returns table (schedule_id uuid, shop_id uuid, account_id uuid)
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select es.id, es.shop_id, s.account_id
    from export_schedules es
    join shops s on s.id = es.shop_id
    join accounts a on a.id = s.account_id
   where es.active
     and a.status = 'active'
     and s.connection_status <> 'deleted'
   order by s.account_id, es.created_at, es.id
$$;

alter function export_schedules_due() owner to mse_migrator;
revoke all on function export_schedules_due() from public;
grant execute on function export_schedules_due() to mse_app;

-- The same closing stance as 0024 and 0028: the two Data API roles must not be able to call
-- the new function, and must hold nothing on the table it reads.
do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anonymous'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      if exists (
        select 1 from information_schema.role_table_grants
         where table_schema = 'public'
           and table_name = 'export_schedules'
           and grantee = r)
      then
        raise exception '0030: role % holds a right on export_schedules', r;
      end if;
      if exists (
        select 1 from pg_proc p
          join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.proname = 'export_schedules_due'
           and has_function_privilege(r, p.oid, 'EXECUTE'))
      then
        raise exception '0030: role % can call export_schedules_due', r;
      end if;
    end if;
  end loop;
end $$;
