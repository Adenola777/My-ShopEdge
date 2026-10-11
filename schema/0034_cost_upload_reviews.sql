-- 0034. The variants a matched cost upload leaves waiting on the seller. Written 11 October 2026,
-- A36 item 5.
--
-- **NOT YET APPLIED to any Neon branch.** Applied on 11 October 2026 to local PostgreSQL 16
-- databases only. See A36.13 for what was checked.
--
-- WHAT THE BRIEF ASKS FOR
--
-- Section 8B of the owner's brief lists four cost statuses for a product: Complete, Cost
-- needed, Partially costed and Needs review. The owner approved building Needs review on
-- 11 October 2026. The first three are worked out from the costs in force (`products.py`).
-- Needs review depends on something the database did not hold: that an upload found a cost
-- for a variant different from the one already set, and the seller has not yet decided.
--
-- WHEN A PRODUCT NEEDS REVIEW. **Derived, not ruled**; the brief names the status only.
--
-- A product needs review while all of these hold for one of its variants:
--   * the shop's latest cost upload has been matched and not applied (`status = 'confirmed'`);
--   * that match found a row for the variant whose cost differs from the cost in force
--     (outcome `needs_review`, A36.9);
--   * no cost has been set for the variant since the match.
-- Applying the upload settles it either way, because the seller chose to replace the cost or
-- to keep it. So does a newer upload, or a cost entered by hand.
--
-- THE TABLE
--
-- One row per variant per upload, written by `matchCostUpload` and cleared by
-- `applyCostUpload`. A match run again replaces the upload's rows. The table holds identifiers
-- and a time only, no personal data, so account erasure has nothing to remove from it.
--
-- Row level security follows `return_items`: a row belongs to the account that owns its shop.

create table cost_upload_reviews (
  cost_upload_id uuid not null references cost_uploads(id) on delete cascade,
  shop_id uuid not null references shops(id),
  sku_id uuid not null references skus(id),
  created_at timestamptz not null default now(),
  primary key (cost_upload_id, sku_id)
);

create index cost_upload_reviews_shop_idx on cost_upload_reviews (shop_id);

alter table cost_upload_reviews enable row level security;
alter table cost_upload_reviews force row level security;

create policy cost_upload_reviews_own on cost_upload_reviews
  using (shop_id in (select id from shops where account_id = app_account_id()))
  with check (shop_id in (select id from shops where account_id = app_account_id()));

grant select, insert, delete on cost_upload_reviews to mse_app;
grant select on cost_upload_reviews to mse_analytics;

comment on table cost_upload_reviews is
  'Variants whose cost a matched, unapplied upload would change. A product with one is Needs review (A36 item 5).';
