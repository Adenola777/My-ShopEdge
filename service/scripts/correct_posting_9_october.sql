-- Corrects the statements posted before 9 October 2026, on the owner's ruling of that day.
--
-- WHY. Production held 107 statements, and 78 did not reconcile. Two TikTok fields repeat
-- another field on the same transaction and were posted as well as it: on every row,
-- affiliate_commission_amount_before_pit equalled affiliate_commission_amount (216 of 216),
-- and tiktok_shop_shipping_incentive_amount equalled shipping_fee_discount_amount (36 of 36).
-- Two more fields were posted as unmapped_fee although their money was right. The posting
-- code was corrected in commit 3c2c475 (tiktok_sync.py, FIELDS CORRECTED). This file corrects
-- what was posted before it.
--
-- HOW. The ledger is append-only (enforce_append_only refuses UPDATE, DELETE and TRUNCATE),
-- so nothing is changed or removed. Every correction is a new entry with source 'system',
-- a reason a seller can read, and, where it cancels an entry, reverses_entry_id naming it.
--   1. Each entry of a repeated field is cancelled by an equal and opposite entry.
--   2. Each smart_promotion_fee_amount and free_return_subsidy_amount entry is cancelled and
--      posted again under its own category, so its money does not move.
--   3. Each statement whose net proceeds rose in step 1 gets a payout entry for the
--      difference, so its entries still come to zero with the payout, as they did before.
-- Every insert names its own source_ref and skips an entry already corrected, so running
-- the file twice adds nothing. The closing check raises, and nothing lands, unless every
-- statement's entries still come to zero and every repeated field is cancelled.
--
-- NOT CORRECTED. seller_discount_refund_amount was never stored, so the three statements it
-- appears to explain (7686421137164715798 by 801, 7679387849959360278 and
-- 7680864799697766167 by 1 each) are left as they are. Correcting them needs TikTok's
-- calculator for their orders read again.
--
-- Rehearsed on production in a transaction that was rolled back, then applied, both on
-- 9 October 2026 as mse_migrator over Neon's SQL-over-HTTPS endpoint, in one transaction.

-- 1. Cancel the repeated fields.
insert into ledger_entries (shop_id, order_id, return_id, settlement_id, entry_type, category,
    amount_minor, currency, occurred_at, basis_month, settlement_month, source, source_ref,
    reverses_entry_id, reason, order_line_id, sku_id, attribution, tiktok_fee_type,
    tiktok_invoice_number, invoice_id)
select le.shop_id, le.order_id, le.return_id, le.settlement_id, le.entry_type, le.category,
    -le.amount_minor, le.currency, le.occurred_at, le.basis_month, le.settlement_month, 'system',
    le.source_ref || ':reversed', le.id,
    'TikTok repeats this figure in another field, which is already counted, so it was counted twice.',
    le.order_line_id, le.sku_id, le.attribution, le.tiktok_fee_type, le.tiktok_invoice_number,
    le.invoice_id
from ledger_entries le
where le.source = 'tiktok'
  and le.tiktok_fee_type in ('affiliate_commission_amount_before_pit', 'tiktok_shop_shipping_incentive_amount')
  and not exists (select 1 from ledger_entries r where r.reverses_entry_id = le.id)
on conflict do nothing;

-- 2a. Cancel the two fields posted without their category.
insert into ledger_entries (shop_id, order_id, return_id, settlement_id, entry_type, category,
    amount_minor, currency, occurred_at, basis_month, settlement_month, source, source_ref,
    reverses_entry_id, reason, order_line_id, sku_id, attribution, tiktok_fee_type,
    tiktok_invoice_number, invoice_id)
select le.shop_id, le.order_id, le.return_id, le.settlement_id, le.entry_type, le.category,
    -le.amount_minor, le.currency, le.occurred_at, le.basis_month, le.settlement_month, 'system',
    le.source_ref || ':reversed', le.id,
    'This figure was filed as a fee MyShopEdge did not recognise. It is filed again under its own name.',
    le.order_line_id, le.sku_id, le.attribution, le.tiktok_fee_type, le.tiktok_invoice_number,
    le.invoice_id
from ledger_entries le
where le.source = 'tiktok' and le.category = 'unmapped_fee'
  and le.tiktok_fee_type in ('smart_promotion_fee_amount', 'free_return_subsidy_amount')
  and not exists (select 1 from ledger_entries r where r.reverses_entry_id = le.id)
on conflict do nothing;

-- 2b. Post them again under their own categories. A return shipping entry names the order's
-- latest return, as tiktok_sync does for every return category.
insert into ledger_entries (shop_id, order_id, return_id, settlement_id, entry_type, category,
    amount_minor, currency, occurred_at, basis_month, settlement_month, source, source_ref,
    reason, order_line_id, sku_id, attribution, tiktok_fee_type, tiktok_invoice_number,
    invoice_id)
select le.shop_id, le.order_id,
    case when le.tiktok_fee_type = 'free_return_subsidy_amount' then
        (select r.id from returns r where r.order_id = le.order_id
         order by r.requested_at desc nulls last limit 1) end,
    le.settlement_id,
    case le.tiktok_fee_type when 'smart_promotion_fee_amount' then 'platform_deduction' else 'return_cost' end,
    case le.tiktok_fee_type when 'smart_promotion_fee_amount' then 'smart_promotions_fee' else 'return_shipping' end,
    le.amount_minor, le.currency, le.occurred_at, le.basis_month, le.settlement_month, 'system',
    le.source_ref || ':recategorised',
    'Filed again under its own name. The amount is TikTok''s, unchanged.',
    le.order_line_id, le.sku_id, le.attribution, le.tiktok_fee_type, le.tiktok_invoice_number,
    le.invoice_id
from ledger_entries le
where le.source = 'tiktok' and le.category = 'unmapped_fee'
  and le.tiktok_fee_type in ('smart_promotion_fee_amount', 'free_return_subsidy_amount')
on conflict do nothing;

-- 3. One payout entry per statement for what step 1 changed, dated as the statement's own
-- payout, so each statement's entries still come to zero.
insert into ledger_entries (shop_id, settlement_id, entry_type, category, amount_minor,
    currency, occurred_at, basis_month, settlement_month, source, source_ref, reason,
    attribution)
select p.shop_id, p.settlement_id, 'payout', 'settlement', -c.moved, p.currency, p.occurred_at,
    p.basis_month, p.settlement_month, 'system', p.source_ref || ':corrected-9-october',
    'The payout is restated because a figure TikTok repeats had been counted twice on this statement.',
    'none'
from ledger_entries p
join (select r.settlement_id, sum(r.amount_minor) moved
      from ledger_entries r
      where r.source = 'system' and r.source_ref like '%:reversed'
        and r.tiktok_fee_type in ('affiliate_commission_amount_before_pit', 'tiktok_shop_shipping_incentive_amount')
      group by r.settlement_id) c on c.settlement_id = p.settlement_id
where p.source = 'tiktok' and p.category = 'settlement' and c.moved <> 0
on conflict do nothing;

-- The closing check. It raises, and the whole transaction is undone, unless all of it holds.
do $$
declare
    unbalanced int;
    uncancelled int;
    unmoved int;
    unreconciled int;
begin
    select count(*) into unbalanced from (
        select settlement_id from ledger_entries
        where settlement_id is not null and entry_type <> 'reserve'
        group by settlement_id having sum(amount_minor) <> 0) x;
    select count(*) into uncancelled from ledger_entries le
    where le.source = 'tiktok'
      and le.tiktok_fee_type in ('affiliate_commission_amount_before_pit', 'tiktok_shop_shipping_incentive_amount')
      and not exists (select 1 from ledger_entries r where r.reverses_entry_id = le.id);
    select count(*) into unmoved from ledger_entries le
    where le.source = 'tiktok' and le.category = 'unmapped_fee'
      and le.tiktok_fee_type in ('smart_promotion_fee_amount', 'free_return_subsidy_amount')
      and not exists (select 1 from ledger_entries r where r.reverses_entry_id = le.id);
    select count(*) into unreconciled from settlement_reconciliation where unexplained_minor <> 0;
    if unbalanced > 0 or uncancelled > 0 or unmoved > 0 then
        raise exception 'correction refused: % statements unbalanced, % repeated entries uncancelled, % unmapped entries unmoved',
            unbalanced, uncancelled, unmoved;
    end if;
    raise notice 'correction holds: % statements still unreconciled', unreconciled;
end
$$;
