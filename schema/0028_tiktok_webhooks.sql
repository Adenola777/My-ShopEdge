-- 0028. The TikTok Shop webhook receiver's store and its two resolvers.
--
-- Written 7 October 2026 to close the second ground of the TikTok Go Live rejection: the
-- webhook receiver the PRD describes and the contract names was not built. It goes on with
-- the owner's authority, as 0022 to 0027 did.
--
-- **NOT YET APPLIED to any Neon branch.** Applied to the local copy only.
--
-- WHY A TABLE AND TWO FUNCTIONS
--
-- A webhook arrives with no bearer token and no account context, carrying only a TikTok shop
-- id. Nothing the service runs as `mse_app` can read a tenant table without a scoped
-- transaction, and the receiver has nothing to scope to until it knows which shop the event
-- is for. So the two things the receiver must do before a tenant is known, record the event
-- for de-duplication and resolve the shop, are done through SECURITY DEFINER functions, in
-- the shape 0017, 0025 and 0027 set: owned by `mse_migrator`, executable by `mse_app` alone,
-- each doing one narrow thing.
--
--   * `tiktok_webhook_events` is the delivery log and the de-duplication key store. Delivery
--     is at least once (TikTok's own documentation), so the receiver records each event under
--     a unique `dedupe_key` and processes it only when the row is new.
--   * `claim_tiktok_webhook` inserts the event if its key is new, resolves the shop and its
--     account from the TikTok shop id, and tells the caller whether the event was new and
--     which shop and account it belongs to. An event for a shop this installation does not
--     hold resolves to null and is acknowledged and ignored, the way the Stripe webhook
--     treats an unknown customer.
--   * `mark_tiktok_webhook` records the outcome of processing, for the webhook log.
--
-- `mse_app` is granted EXECUTE on the two functions and nothing on the table, so the table is
-- reached only through them. Migration 0024 removed `mse_migrator`'s default privileges, so
-- this new table grants nothing to `authenticated` or `anonymous`; the closing check proves
-- it.

create table tiktok_webhook_events (
  id              uuid primary key default gen_random_uuid(),
  dedupe_key      text not null unique,
  notification_id text,
  event_type      text,
  tiktok_shop_id  text,
  shop_id         uuid references shops(id),
  payload         jsonb,
  received_at     timestamptz not null default now(),
  processed_at    timestamptz,
  process_status  text,
  process_note    text
);

alter table tiktok_webhook_events owner to mse_migrator;
revoke all on tiktok_webhook_events from public;

create index tiktok_webhook_events_shop_received_idx
  on tiktok_webhook_events (shop_id, received_at desc);
create index tiktok_webhook_events_unprocessed_idx
  on tiktok_webhook_events (received_at) where processed_at is null;

-- Record the event if its key is new, and resolve the shop and account from the TikTok shop
-- id. `is_new` is false when the key was seen before, which is how a redelivery is dropped.
create or replace function claim_tiktok_webhook(
    p_dedupe_key text,
    p_notification_id text,
    p_event_type text,
    p_tiktok_shop_id text,
    p_payload jsonb)
  returns table (is_new boolean, shop_id uuid, account_id uuid)
  language plpgsql
  security definer
  set search_path = public, pg_temp
as $$
declare
  v_shop uuid;
  v_account uuid;
  v_new boolean;
begin
  select s.id, s.account_id into v_shop, v_account
    from shops s
   where s.tiktok_shop_id = p_tiktok_shop_id
   order by s.id
   limit 1;

  insert into tiktok_webhook_events
      (dedupe_key, notification_id, event_type, tiktok_shop_id, shop_id, payload)
  values (p_dedupe_key, p_notification_id, p_event_type, p_tiktok_shop_id, v_shop, p_payload)
  on conflict (dedupe_key) do nothing;

  -- FOUND reflects the insert just run: true when a row went in, false on a conflict.
  v_new := found;

  return query select v_new, v_shop, v_account;
end;
$$;

alter function claim_tiktok_webhook(text, text, text, text, jsonb) owner to mse_migrator;
revoke all on function claim_tiktok_webhook(text, text, text, text, jsonb) from public;
grant execute on function claim_tiktok_webhook(text, text, text, text, jsonb) to mse_app;

create or replace function mark_tiktok_webhook(p_dedupe_key text, p_status text, p_note text)
  returns void
  language sql
  security definer
  set search_path = public, pg_temp
as $$
  update tiktok_webhook_events
     set process_status = p_status,
         process_note = left(p_note, 1000),
         processed_at = now()
   where dedupe_key = p_dedupe_key
$$;

alter function mark_tiktok_webhook(text, text, text) owner to mse_migrator;
revoke all on function mark_tiktok_webhook(text, text, text) from public;
grant execute on function mark_tiktok_webhook(text, text, text) to mse_app;

-- The same closing stance as 0024, guarded the same way on the role existing, because a
-- branch without Neon Auth holds neither role: the two unprivileged roles must hold nothing
-- on the new table and must not be able to call the new functions.
do $$
declare
  r text;
begin
  foreach r in array array['authenticated', 'anonymous'] loop
    if exists (select 1 from pg_roles where rolname = r) then
      if exists (
        select 1 from information_schema.role_table_grants
         where table_schema = 'public'
           and table_name = 'tiktok_webhook_events'
           and grantee = r)
      then
        raise exception '0028: role % holds a right on tiktok_webhook_events', r;
      end if;
      if exists (
        select 1 from pg_proc p
          join pg_namespace n on n.oid = p.pronamespace
         where n.nspname = 'public'
           and p.proname in ('claim_tiktok_webhook', 'mark_tiktok_webhook')
           and has_function_privilege(r, p.oid, 'EXECUTE'))
      then
        raise exception '0028: role % can call a webhook function', r;
      end if;
    end if;
  end loop;
end $$;
