-- 0032. The admin backend's read paths (A34). Written 10 October 2026.
--
-- **NOT YET APPLIED to any Neon branch.** Applied on 10 October 2026 to a local PostgreSQL 16
-- built from empty by `migrate.py` only, where `testdata/admin_check.py` ran against it.
--
-- WHY FUNCTIONS
--
-- Row level security shows `mse_app` one account at a time (0003), and no role reads across
-- accounts (A34.2). The admin views need to. A34.4 ruled that each view is one SECURITY DEFINER
-- function, in the shape 0017 to 0031 set: owned by `mse_migrator`, executable by `mse_app`
-- alone, returning only the columns it names. None of them returns a TikTok token, the
-- webhook payload, or any money figure of a seller (A34.8, ruling 4). The gate is
-- `require_admin` in `service/app/admin.py`; these functions are reachable only through it.
--
-- The admin's actions (suspend, reactivate, sync, retry an email, export, deletion) need no
-- function here. Each runs inside `tenant()` for the one account it acts on, under row level
-- security, exactly as the seller's own request would.
--
-- Every function is read only and takes at most a row limit, capped at 500.

create or replace function admin_accounts()
  returns table (
    account_id uuid, email text, display_name text, status text, created_at timestamptz,
    deleted_at timestamptz, erased_at timestamptz, email_notices boolean, plan_slug text,
    plan_status text, trial_end timestamptz, current_period_end timestamptz,
    cancel_at_period_end boolean, shop_count bigint)
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select a.id, a.email::text, a.display_name, a.status, a.created_at, a.deleted_at,
         a.erased_at, a.email_notices, sub.plan_slug, sub.status, sub.trial_end,
         sub.current_period_end, sub.cancel_at_period_end,
         (select count(*) from shops s
           where s.account_id = a.id and s.connection_status <> 'deleted')
    from accounts a
    left join subscriptions sub on sub.account_id = a.id
   order by a.created_at desc, a.id
$$;

create or replace function admin_shops()
  returns table (
    shop_id uuid, account_id uuid, account_email text, shop_name text, tiktok_shop_code text,
    region text, seller_type text, connection_status text, first_synced_at timestamptz,
    last_synced_at timestamptz, access_expires_at timestamptz,
    refresh_succeeded_at timestamptz, refresh_failure_code text,
    refresh_failure_reason text, revoked_at timestamptz, statements bigint,
    statements_unexplained bigint)
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select s.id, s.account_id, a.email::text, s.shop_name, s.tiktok_shop_code, s.region,
         s.seller_type, s.connection_status, s.first_synced_at, s.last_synced_at,
         c.access_expires_at, c.refresh_succeeded_at, c.refresh_failure_code,
         c.refresh_failure_reason, c.revoked_at,
         (select count(*) from settlement_reconciliation r where r.shop_id = s.id),
         (select count(*) from settlement_reconciliation r
           where r.shop_id = s.id and r.unexplained_minor <> 0)
    from shops s
    join accounts a on a.id = s.account_id
    left join tiktok_connections c on c.shop_id = s.id
   order by s.created_at desc, s.id
$$;

create or replace function admin_sync_runs(p_limit integer)
  returns table (
    run_id uuid, shop_id uuid, shop_name text, kind text, domain text, status text,
    started_at timestamptz, finished_at timestamptz, records_read integer,
    records_written integer, records_failed integer, error text)
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select r.id, r.shop_id, s.shop_name, r.kind, r.domain, r.status, r.started_at,
         r.finished_at, r.records_read, r.records_written, r.records_failed, r.error
    from sync_runs r
    join shops s on s.id = r.shop_id
   order by coalesce(r.started_at, r.created_at) desc, r.id
   limit least(greatest(p_limit, 1), 500)
$$;

create or replace function admin_webhook_events(p_limit integer)
  returns table (
    event_id uuid, received_at timestamptz, event_type text, tiktok_shop_id text,
    shop_id uuid, processed_at timestamptz, process_status text, process_note text)
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select e.id, e.received_at, e.event_type, e.tiktok_shop_id, e.shop_id, e.processed_at,
         e.process_status, e.process_note
    from tiktok_webhook_events e
   order by e.received_at desc, e.id
   limit least(greatest(p_limit, 1), 500)
$$;

create or replace function admin_email_counts()
  returns table (email_status text, notices bigint)
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select n.email_status, count(*) from notifications n group by n.email_status
   order by n.email_status
$$;

create or replace function admin_email_problems(p_limit integer)
  returns table (
    notification_id uuid, account_id uuid, account_email text, type text,
    created_at timestamptz, email_status text, email_attempts smallint, email_note text)
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select n.id, n.account_id, a.email::text, n.type, n.created_at, n.email_status,
         n.email_attempts, n.email_note
    from notifications n
    join accounts a on a.id = n.account_id
   where n.email_status in ('failed', 'pending')
   order by n.created_at desc, n.id
   limit least(greatest(p_limit, 1), 500)
$$;

create or replace function admin_audit(p_limit integer)
  returns table (
    audit_id uuid, occurred_at timestamptz, account_id uuid, actor text, action text,
    entity_type text, entity_id uuid)
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select l.id, l.occurred_at, l.account_id, l.actor, l.action, l.entity_type, l.entity_id
    from audit_log l
   order by l.occurred_at desc, l.id
   limit least(greatest(p_limit, 1), 500)
$$;

do $$
declare
  f text;
begin
  foreach f in array array[
    'admin_accounts()', 'admin_shops()', 'admin_sync_runs(integer)',
    'admin_webhook_events(integer)', 'admin_email_counts()', 'admin_email_problems(integer)',
    'admin_audit(integer)']
  loop
    execute format('alter function %s owner to mse_migrator', f);
    execute format('revoke all on function %s from public', f);
    execute format('grant execute on function %s to mse_app', f);
  end loop;
end $$;

-- The same closing stance as 0024, 0028, 0030 and 0031: the two Data API roles must not be
-- able to call any of the new functions.
do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anonymous'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      if exists (
        select 1 from pg_proc p
          join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.proname like 'admin\_%'
           and has_function_privilege(r, p.oid, 'EXECUTE'))
      then
        raise exception '0032: role % can call an admin function', r;
      end if;
    end if;
  end loop;
end $$;
