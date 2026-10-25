-- 0037. A TikTok approval that arrived without a state MyShopEdge issued, held until the seller
-- signs in and confirms the shop. Written 25 October 2026.
--
-- **NOT YET APPLIED to any Neon branch.** Applied on 25 October 2026 to local PostgreSQL 16
-- databases only. See CLAUDE.md, the TikTok Go Live review section, for what was checked.
--
-- WHY THIS EXISTS
--
-- Until now a connection had to start from "Connect TikTok Shop" inside MyShopEdge, which
-- issues a `state` (0021), and the callback refused any approval without one. A seller who
-- installs the app from TikTok's App & Service Store starts on TikTok's side instead, and
-- whether TikTok then sends any state is unverified. TikTok's reviewers may take that route,
-- and on 25 October 2026 the owner approved accepting it.
--
-- TikTok's code is short-lived, so the callback exchanges it at once. With no state there is
-- no account to attach the shop to, so the tokens wait here, encrypted as in
-- `tiktok_connections`, behind a one-time claim value held in the seller's browser. The
-- seller signs in, is shown the shop's name, and confirms; only then is the shop attached.
-- The confirmation is what stands in for the state: without it, somebody could send a victim
-- a link carrying their own approval and attach their shop to the victim's account.
--
-- A row lives thirty minutes and is deleted when claimed, so tokens are not kept here beyond
-- the hand-over. The table carries no account, so no tenant may read it: row level security
-- is forced with no policy, `mse_app` holds no right on the table, and the two SECURITY
-- DEFINER functions below are the only way in.

create table tiktok_pending_connections (
  id uuid primary key default gen_random_uuid(),
  claim_sha256 text not null unique,
  access_token_enc bytea not null,
  refresh_token_enc bytea not null,
  access_expires_at timestamptz,
  refresh_expires_at timestamptz,
  scopes text[] not null default '{}',
  key_version integer not null default 1,
  -- The shops TikTok listed: id, code, name, region, seller_type, and the shop cipher
  -- encrypted and base64 encoded. Never a token.
  shops jsonb not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null
);

alter table tiktok_pending_connections enable row level security;
alter table tiktok_pending_connections force row level security;
revoke all on tiktok_pending_connections from public;

comment on table tiktok_pending_connections is
  'A TikTok approval with no state of ours, waiting for the seller to sign in and confirm the '
  'shop. Thirty minutes, deleted when claimed. No tenant reads it; the functions below do.';

create or replace function create_tiktok_pending_connection(
  p_claim_sha256       text,
  p_access_token_enc   bytea,
  p_refresh_token_enc  bytea,
  p_access_expires_at  timestamptz,
  p_refresh_expires_at timestamptz,
  p_scopes             text[],
  p_key_version        integer,
  p_shops              jsonb,
  p_expires_at         timestamptz
) returns uuid
  language plpgsql
  security definer
  set search_path = public, pg_temp
as $$
declare
  v_id uuid;
begin
  -- Expired rows hold tokens nobody can claim, so each new row clears them.
  delete from tiktok_pending_connections where expires_at < now();

  insert into tiktok_pending_connections
    (claim_sha256, access_token_enc, refresh_token_enc, access_expires_at, refresh_expires_at,
     scopes, key_version, shops, expires_at)
  values
    (p_claim_sha256, p_access_token_enc, p_refresh_token_enc, p_access_expires_at,
     p_refresh_expires_at, coalesce(p_scopes, '{}'), p_key_version, p_shops, p_expires_at)
  returning id into v_id;
  return v_id;
end
$$;

alter function create_tiktok_pending_connection(text, bytea, bytea, timestamptz, timestamptz,
  text[], integer, jsonb, timestamptz) owner to mse_migrator;
revoke all on function create_tiktok_pending_connection(text, bytea, bytea, timestamptz,
  timestamptz, text[], integer, jsonb, timestamptz) from public;
grant execute on function create_tiktok_pending_connection(text, bytea, bytea, timestamptz,
  timestamptz, text[], integer, jsonb, timestamptz) to mse_app;

-- Spends a claim: returns the waiting approval and deletes it, in one statement, so a claim
-- works once. An unknown, expired or spent claim returns no row, and the three are not told
-- apart, as with consume_tiktok_auth_state.
create or replace function claim_tiktok_pending_connection(p_claim_sha256 text)
  returns table (
    access_token_enc bytea,
    refresh_token_enc bytea,
    access_expires_at timestamptz,
    refresh_expires_at timestamptz,
    scopes text[],
    key_version integer,
    shops jsonb
  )
  language sql
  volatile
  security definer
  set search_path = public, pg_temp
as $$
  delete from tiktok_pending_connections p
   where p.claim_sha256 = p_claim_sha256
     and p.expires_at > now()
  returning p.access_token_enc, p.refresh_token_enc, p.access_expires_at, p.refresh_expires_at,
            p.scopes, p.key_version, p.shops
$$;

alter function claim_tiktok_pending_connection(text) owner to mse_migrator;
revoke all on function claim_tiktok_pending_connection(text) from public;
grant execute on function claim_tiktok_pending_connection(text) to mse_app;

-- The closing stance of 0024, 0028, 0031 and 0036: the Data API roles hold nothing on the new
-- table and cannot call either function, and the application role reaches the table only
-- through the functions.
do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anonymous', 'mse_app'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      if exists (
        select 1 from information_schema.role_table_grants
         where table_schema = 'public'
           and table_name = 'tiktok_pending_connections'
           and grantee = r)
      then
        raise exception '0037: role % holds a right on tiktok_pending_connections', r;
      end if;
    end if;
  end loop;
  foreach r in array array['authenticated', 'anonymous'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      if exists (
        select 1 from pg_proc p
          join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.proname in ('create_tiktok_pending_connection', 'claim_tiktok_pending_connection')
           and has_function_privilege(r, p.oid, 'EXECUTE'))
      then
        raise exception '0037: role % can call a pending connection function', r;
      end if;
    end if;
  end loop;
end $$;
