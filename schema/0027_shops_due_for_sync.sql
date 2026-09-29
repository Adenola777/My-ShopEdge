-- 0027. The shops the TikTok sync job reads. Part 1 of the batch approved on 29 September 2026.
--
-- The sync job runs as `mse_app`, like every other part of the service, and row level
-- security lets `mse_app` see one account at a time. Nothing else could find the shops to
-- sync. `shops_due_for_sync()` follows the shape 0017, 0018 and 0025 set: SECURITY DEFINER,
-- one statement, owned by `mse_migrator`, executable by `mse_app` alone. It returns ids and
-- nothing else. The sync of each shop then runs inside `tenant()`, under row level security.
--
-- A shop is listed when its connection has not been revoked, the shop is not disconnected,
-- and TikTok gave the region and seller type the MVP reads (GB and LOCAL, see
-- `app/connections.py`). A shop that fails either test is stored but never produces figures,
-- which is what ConnectionResult.accepted = false promises. A closing or erased account is
-- not synced, because A30.1 stops new data arriving once a deletion is requested.
--
-- NOT YET APPLIED to any Neon branch. Applied to the local copy only, on 29 September 2026.

create or replace function shops_due_for_sync()
  returns table (shop_id uuid, account_id uuid)
  language sql
  stable
  security definer
  set search_path = public, pg_temp
as $$
  select s.id, s.account_id
    from shops s
    join accounts a on a.id = s.account_id
    join tiktok_connections c on c.shop_id = s.id
   where a.status = 'active'
     and s.connection_status in ('pending', 'connected', 'needs_reconnect')
     and s.region = 'GB'
     and s.seller_type = 'LOCAL'
     and c.revoked_at is null
   order by s.last_synced_at nulls first, s.id
$$;

alter function shops_due_for_sync() owner to mse_migrator;
revoke all on function shops_due_for_sync() from public;
grant execute on function shops_due_for_sync() to mse_app;
