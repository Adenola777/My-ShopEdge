-- 0036. The billing cycle, the date a plan is set to end, and the end of a twelve-payment term.
-- Written 11 October 2026, A38.6.
--
-- **NOT YET APPLIED to any Neon branch.** Applied on 11 October 2026 to local PostgreSQL 16
-- databases only. See A38.6 for what was checked.
--
-- WHY THIS EXISTS
--
-- On 11 October 2026 the owner approved the nine A38 prices and asked for the commitment behind
-- Annual, billed monthly to be built: a seller on that cycle owes all twelve payments, even
-- after stopping renewal. The service keeps that promise by asking Stripe to cancel on the day
-- the twelfth payment's month ends, rather than at the end of the current month. The app must
-- then show that date, and the row held neither the cycle nor any date but the period's end.
--
--   cycle               annual, annual_monthly or monthly, from the price the plan is on
--   cancel_at           the day Stripe will end the plan, when one is set, else null
--   commitment_ends_at  the end of the running twelve-payment term, on annual_monthly only
--
-- The columns are written by their own function rather than by widening
-- apply_subscription_event, so the function the webhook already calls on production is not
-- replaced. Both are called from the same write path in billing.py.

alter table subscriptions
  add column cycle text check (cycle in ('annual', 'annual_monthly', 'monthly')),
  add column cancel_at timestamptz,
  add column commitment_ends_at timestamptz;

comment on column subscriptions.cycle is
  'The billing cycle of the price the plan is on (A38.1). Null before the price is known.';
comment on column subscriptions.cancel_at is
  'When Stripe will end the plan, if a date is set. Used for a stopped Annual, billed monthly plan (A38.6).';
comment on column subscriptions.commitment_ends_at is
  'The end of the running twelve-payment term of Annual, billed monthly (A38.6). Null on other cycles.';

create or replace function apply_subscription_terms(
  p_stripe_customer_id text,
  p_cycle              text,
  p_cancel_at          timestamptz,
  p_commitment_ends_at timestamptz
) returns uuid
  language plpgsql
  security definer
  set search_path = public, pg_temp
as $$
declare
  v_id uuid;
begin
  -- Not coalesced: a null cancel_at means renewal is on, and a null commitment means none.
  update subscriptions set
    cycle              = p_cycle,
    cancel_at          = p_cancel_at,
    commitment_ends_at = p_commitment_ends_at,
    updated_at         = now()
  where stripe_customer_id = p_stripe_customer_id
  returning id into v_id;

  if v_id is null then
    raise exception 'unknown_stripe_customer'
      using hint = 'No subscription row carries this customer id.';
  end if;
  return v_id;
end
$$;

alter function apply_subscription_terms(text, text, timestamptz, timestamptz) owner to mse_migrator;
revoke all on function apply_subscription_terms(text, text, timestamptz, timestamptz) from public;
grant execute on function apply_subscription_terms(text, text, timestamptz, timestamptz) to mse_app;

-- The same closing stance as 0024, 0028 and 0031: the two Data API roles must hold nothing on
-- the table this changes and must not be able to call the new function.
do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anonymous'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      if exists (
        select 1 from information_schema.role_table_grants
         where table_schema = 'public'
           and table_name = 'subscriptions'
           and grantee = r)
      then
        raise exception '0036: role % holds a right on subscriptions', r;
      end if;
      if exists (
        select 1 from pg_proc p
          join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.proname = 'apply_subscription_terms'
           and has_function_privilege(r, p.oid, 'EXECUTE'))
      then
        raise exception '0036: role % can call apply_subscription_terms', r;
      end if;
    end if;
  end loop;
end $$;
