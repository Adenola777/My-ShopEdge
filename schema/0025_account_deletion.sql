-- 0025. Account deletion under A30.1: close at once, erase after thirty days.
--
-- Written 28 September 2026. Applied to the local copy of development only. **Not applied
-- to any Neon branch.** It goes on with the owner's authority, as 0022 to 0024 did.
--
-- WHAT A30.1 NEEDS FROM THE SCHEMA
--
-- A deletion sets `accounts.status` to 'deleted' and `deleted_at` to the moment of the
-- request. Both columns exist since the first schema. The grace period ends thirty days
-- after `deleted_at`, and the service derives that date rather than storing it, so a
-- cancellation has one column to clear.
--
-- Three things are new.
--
-- `accounts.erased_at` records that the thirty days ended and the erasure ran: the name and
-- email are gone, the stored TikTok tokens are gone and the account's files are deleted.
-- Without it, the only sign of an erased account would be the shape of its placeholder
-- email, and the job must not decide what to do from the shape of a string.
--
-- `accounts_due_for_erasure()` lists the accounts whose thirty days have ended and which
-- are not yet erased. The erasure job runs as `mse_app`, and row level security lets
-- `mse_app` see one account at a time, so nothing else could find them. The function
-- follows the shape 0017 and 0018 set: SECURITY DEFINER, one statement, owned by
-- `mse_migrator`, executable by `mse_app` alone. It returns ids and nothing else. The
-- erasure itself runs per account inside `tenant()`, under row level security.
--
-- `account_of_subject(subject)` returns the id and status of the account a verified subject
-- belongs to, whatever its status. `resolve_account` returns active accounts only, so a
-- closing account used to fall through to the first sign-in path, which needs an email
-- address. On the local copy on 28 September a closing account whose token carried no
-- email was answered 503 `identity_syncing` on every request and could never reach the
-- cancellation A30.1 allows. The service now asks this function first. It has the same
-- shape as `resolve_account`: SECURITY DEFINER, one statement, `mse_app` alone.

alter table accounts add column if not exists erased_at timestamptz;

alter table accounts drop constraint if exists accounts_erased_only_when_deleted;
alter table accounts add constraint accounts_erased_only_when_deleted
  check (erased_at is null or (status = 'deleted' and deleted_at is not null));

create or replace function accounts_due_for_erasure()
  returns setof uuid
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select id from accounts
   where status = 'deleted'
     and erased_at is null
     and deleted_at <= now() - interval '30 days'
   order by deleted_at
$$;

alter function accounts_due_for_erasure() owner to mse_migrator;
revoke all on function accounts_due_for_erasure() from public;
grant execute on function accounts_due_for_erasure() to mse_app;

create or replace function account_of_subject(p_subject text)
  returns table (id uuid, status text)
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select a.id, a.status from accounts a where a.auth_subject = p_subject
$$;

alter function account_of_subject(text) owner to mse_migrator;
revoke all on function account_of_subject(text) from public;
grant execute on function account_of_subject(text) to mse_app;
