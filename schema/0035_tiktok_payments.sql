-- 0035. TikTok's own list of payouts, so a payout with no statement can be shown as Unmatched.
-- Written 11 October 2026, A36 item 6.
--
-- **NOT YET APPLIED to any Neon branch.** Applied on 11 October 2026 to local PostgreSQL 16
-- databases only. See A36.14 for what was checked.
--
-- WHY THIS EXISTS
--
-- The owner ruled on 10 October 2026 that Unmatched is "a payout with no statement behind it"
-- (A36.2 answer 2). MyShopEdge read payouts only inside statements, so it could never hold one
-- without a statement. On 11 October 2026 the owner amended A11.5 so that
-- `GET /finance/202309/payments` may be read for that one purpose. Bank reconciliation stays
-- out of scope: nothing here is matched to a bank account.
--
-- WHAT A ROW HOLDS. The fields are from TikTok's "Get Payments" page, whose response example
-- the owner pasted on 11 October 2026.
--
--   id                              -> tiktok_payment_id, which statements carry as payment_id
--   status                          -> status, as TikTok gives it ("PAID" in the example)
--   amount                          -> amount_minor
--   settlement_amount               -> settlement_amount_minor
--   reserve_amount                  -> reserve_amount_minor
--   amount.currency                 -> currency
--   create_time, paid_time          -> created_at, paid_at, from Unix seconds
--
-- `bank_account` is in the answer, masked by TikTok. It is not stored, because nothing here
-- needs it and bank reconciliation is out of scope. `payment_amount_before_exchange` and
-- `exchange_rate` are not stored either, because only GBP is read (A20.3).
--
-- **Unverified:** that the amounts are in pounds rather than pence. The example's "100" could
-- be either. They are read as the statements' amounts are, in major units, and the first real
-- payment compared with its statement settles it.
--
-- Row level security follows `settlements`: a row belongs to the account that owns its shop.

create table tiktok_payments (
  id uuid primary key default gen_random_uuid(),
  shop_id uuid not null references shops(id),
  tiktok_payment_id text not null,
  status text,
  amount_minor bigint not null,
  settlement_amount_minor bigint,
  reserve_amount_minor bigint,
  currency text not null,
  created_at timestamptz,
  paid_at timestamptz,
  read_at timestamptz not null default now(),
  unique (shop_id, tiktok_payment_id)
);

alter table tiktok_payments enable row level security;
alter table tiktok_payments force row level security;

create policy tiktok_payments_own on tiktok_payments
  using (shop_id in (select id from shops where account_id = app_account_id()))
  with check (shop_id in (select id from shops where account_id = app_account_id()));

grant select, insert, update on tiktok_payments to mse_app;
grant select on tiktok_payments to mse_analytics;

comment on table tiktok_payments is
  'TikTok payouts from Get Payments. One with no statement carrying its id is Unmatched (A36 item 6).';
