-- 0026. What the export jobs need to report, and somewhere to keep an account's data download.
--
-- Written 29 September 2026. Applied to the local copy of development only. **Not applied to
-- any Neon branch.** It goes on with the owner's authority, as 0022 to 0025 did.
--
-- SHOP EXPORTS
--
-- The contract's ShopExportJob serves `ready_at`, `size_bytes` and `row_count`, and S23 must
-- say what failed when a build fails. `exports` held none of the four, so a finished job
-- could not say when it finished, how large its file is or how many rows it holds.
--
-- ACCOUNT EXPORTS
--
-- `requestAccountExport` (ACC-4) returns a job the seller polls. The Data Protection document
-- promises "Portability (Art. 20) Machine-readable export (CSV and JSON)". No table held such
-- a job, because `exports` belongs to a shop and a data download belongs to the account. The
-- file goes under A10.8's `account-exports/{account_id}/{request_id}/{nonce}.zip`, and the
-- erasure job of A30.1 already deletes that prefix.
--
-- The table follows the shape of every tenant table: row level security forced, one policy
-- scoping it to `app_account_id()`, and `mse_app` holding what the service needs.

alter table exports add column if not exists ready_at timestamptz;
alter table exports add column if not exists size_bytes bigint check (size_bytes >= 0);
alter table exports add column if not exists row_count integer check (row_count >= 0);
alter table exports add column if not exists failure_reason text;

create table if not exists account_exports (
  id             uuid primary key default gen_random_uuid(),
  account_id     uuid not null references accounts(id),
  status         text not null default 'queued'
                 check (status in ('queued', 'ready', 'failed', 'expired')),
  storage_key    text,
  requested_at   timestamptz not null default now(),
  ready_at       timestamptz,
  expires_at     timestamptz,
  size_bytes     bigint check (size_bytes >= 0),
  failure_reason text
);

create index if not exists account_exports_account_idx on account_exports (account_id, requested_at desc);

alter table account_exports enable row level security;
alter table account_exports force row level security;

drop policy if exists account_exports_own on account_exports;
create policy account_exports_own on account_exports
  using (account_id = app_account_id())
  with check (account_id = app_account_id());

grant select, insert, update on account_exports to mse_app;
grant select on account_exports to mse_analytics;
