-- 0031. Notices sent by email, and the seller's switch to stop them. Written 10 October 2026,
-- when the owner chose Resend as the email provider and asked for the email side to be built.
--
-- **NOT YET APPLIED to any Neon branch.** Applied on 10 October 2026 to local PostgreSQL 16
-- databases only: one built from empty by `migrate.py`, on which `testdata/notice_email_check.py`
-- passed 35 of 35, and one that already held a notice from before 0031, where that notice took
-- `predates_email`, a notice written afterwards took `pending`, and `mse_app` listed one account
-- through `notices_due_for_email()` while seeing no notice outside `tenant()`.
--
-- WHAT THE RULINGS ASK FOR
--
--   * NTF-2 (SRD): "Email the seller about critical events (connection revoked, feed failing)
--     unless they opt out." Acceptance: "Opted-out sellers receive no email."
--   * The SRD's interfaces table: "Transactional email for verification and critical notices
--     only."
--   * A16.3: at 100 per cent of the plan's orders "an email is sent".
--   * A5.7: a scheduled export's seller "is told in the app and, if they have not opted out,
--     by email".
--
-- Which notice types are emailed is a business rule, so it lives in Python
-- (`app/notice_email.py`, A29). The database holds only what each notice's email did.
--
-- THE SWITCH, `accounts.email_notices`
--
-- One switch per account, because notices belong to the account (NTF-1) and every ruling
-- above speaks of one opt-out. It is on by default, because NTF-2 sends "unless they opt out".
--
-- THE STATE OF EACH NOTICE'S EMAIL, `notifications.email_status`
--
--   pending          not yet considered by the sender
--   sent             Resend accepted it; `emailed_at` is when, `email_note` holds Resend's id
--   not_emailed      considered and deliberately not sent; `email_note` says why
--   failed           Resend refused it three times; `email_note` holds the last refusal
--   predates_email   written before this migration
--
-- The column is added with the default `predates_email`, so every notice already on a branch
-- takes that value and is never emailed, and the default then becomes `pending` for every
-- notice written afterwards. Without this, the first run after the migration would email
-- every seller about every notice they have ever had. Adding a column with a constant default
-- rewrites no row in PostgreSQL 11 and later.
--
-- THE SENDER'S LIST, `notices_due_for_email()`
--
-- The daily job runs as `mse_app`, and row level security shows it one account at a time, so
-- it cannot find the accounts that have notices waiting. The function follows the shape 0017,
-- 0025, 0027 and 0030 set: SECURITY DEFINER, one statement, owned by `mse_migrator`,
-- executable by `mse_app` alone, and it returns ids and nothing else. The sender then reads
-- and updates each notice inside `tenant()`, under row level security.

alter table accounts add column email_notices boolean not null default true;

alter table notifications
  add column email_status text not null default 'predates_email'
    check (email_status in ('pending', 'sent', 'not_emailed', 'failed', 'predates_email')),
  add column emailed_at timestamptz,
  add column email_attempts smallint not null default 0 check (email_attempts >= 0),
  add column email_note text;

alter table notifications alter column email_status set default 'pending';

create index notifications_email_pending_idx
  on notifications (created_at) where email_status = 'pending';

create or replace function notices_due_for_email()
  returns table (account_id uuid)
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select n.account_id
    from notifications n
   where n.email_status = 'pending'
   group by n.account_id
   order by min(n.created_at), n.account_id
$$;

alter function notices_due_for_email() owner to mse_migrator;
revoke all on function notices_due_for_email() from public;
grant execute on function notices_due_for_email() to mse_app;

-- The same closing stance as 0024, 0028 and 0030: the two Data API roles must hold nothing on
-- the two tables this changes and must not be able to call the new function.
do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anonymous'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      if exists (
        select 1 from information_schema.role_table_grants
         where table_schema = 'public'
           and table_name in ('accounts', 'notifications')
           and grantee = r)
      then
        raise exception '0031: role % holds a right on accounts or notifications', r;
      end if;
      if exists (
        select 1 from pg_proc p
          join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.proname = 'notices_due_for_email'
           and has_function_privilege(r, p.oid, 'EXECUTE'))
      then
        raise exception '0031: role % can call notices_due_for_email', r;
      end if;
    end if;
  end loop;
end $$;
