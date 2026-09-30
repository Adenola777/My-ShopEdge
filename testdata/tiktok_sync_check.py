"""Runs the TikTok sync (service/app/tiktok_sync.py) against the generated payloads.

    createdb mse_sync
    DATABASE_URL=... python3 service/scripts/migrate.py
    DATABASE_URL=... python3 testdata/tiktok_sync_check.py

Written 29 September 2026 for part 1 of the batch. It needs a database, so it is not in CI.
The database must be built from empty by `migrate.py` and must be a local copy: the script
creates an account, a shop and a connection in it.

Nothing here reaches TikTok. A transport answers each request from `testdata/payloads` (or
the directory in MSE_PAYLOADS), the same files `ingest.py` reads, so the check compares two
independent readings of one set of payloads: the service's, and the ingester's `rows.json`.

What it checks:
- Every request is signed, and every listing sends the sort field and order A19.4 requires.
- The ledger the sync writes equals, category by category, the settled part of `rows.json`,
  leaving out `cost_of_goods_sold` and `stock_written_off`, which the sync does not post.
- Every settlement's payout is the negative of its own entries, and the statement count,
  the order count and the return count match the payloads.
- A second run over the same window writes nothing.
- A token with fewer than two days left is refreshed and stored encrypted, and a refused
  refresh is recorded with TikTok's code without touching the stored token.

**Run on 29 September 2026** against databases built from empty by `migrate.py`: 36 of 36
passed on `payloads` with `rows.json`, and 36 of 36 on `payloads_year` with `rows_year.json`.
Rerun the same day after the token expiry fault (CLAUDE.md fault 11), with the refresh
answering Unix times as TikTok does: 36 of 36 on both again.
Rerun after A31.7, with a second shop sharing the authorisation: 37 of 37 on both.
Rerun on 30 September 2026 with the stock read (A32) and STK-8's cases TC-STK-08 to 11:
45 of 45 on both datasets.
"""

import base64
import json
import os
import secrets
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "service"))

os.environ.setdefault("TIKTOK_APP_KEY", "check-app-key")
os.environ.setdefault("TIKTOK_APP_SECRET", "check-app-secret")
os.environ.setdefault("TIKTOK_TOKEN_KEY", base64.b64encode(secrets.token_bytes(32)).decode())

import psycopg  # noqa: E402

from app import tiktok_api, tiktok_sync  # noqa: E402
from app.connections import _encrypt  # noqa: E402

P = HERE / os.environ.get("MSE_PAYLOADS", "payloads")
ROWS = HERE / os.environ.get("MSE_ROWS", "rows.json")


def load(name):
    return json.load(open(P / name))


SHOPS = load("authorization_shops.json")["data"]["shops"]
ORDERS = load("orders.json")["data"]["orders"]
STATEMENTS = load("statements.json")["data"]["statements"]
STMT_TXNS = load("statement_transactions.json")
ORDER_CALC = load("order_statement_transactions.json")
RETURNS = load("returns.json")["data"]["return_orders"]
INVENTORY = load("inventory.json")["data"]["inventory"]
LIVE_INVENTORY = json.load(open(HERE / "live" / "inventory_search_my_shopedge_30_september.json"))["data"]
# The check moves TikTok's count for one variant to test absorption (STK-8).
STOCK_OVERRIDE: dict[str, int] = {}

ok = bad = 0
calls: list[tuple[str, str, dict]] = []


def check(cond, what):
    global ok, bad
    print(("PASS " if cond else "FAIL ") + what)
    ok += bool(cond)
    bad += not cond


def answer(data):
    return {"code": 0, "message": "Success", "data": data}


NEW_ACCESS_EXPIRES = 1791309162


def fake(method, url, params, headers, body):
    """Answers as TikTok would, from the payload files. Records every request it receives."""
    path = urlparse(url).path
    calls.append((method, path, dict(params)))
    if url == tiktok_api.REFRESH_URL:
        if os.environ.get("_CHECK_REFUSE_REFRESH"):
            return {"code": 36004001, "message": "refresh token invalid", "data": None}
        # Unix times, as the first real authorisation returned them on 29 September 2026.
        return answer({"access_token": "new-access", "access_token_expire_in": NEW_ACCESS_EXPIRES,
                       "refresh_token": "new-refresh", "refresh_token_expire_in": 4912765591})
    if path == tiktok_api.STATEMENTS_PATH:
        ge, lt = int(params["statement_time_ge"]), int(params["statement_time_lt"])
        return answer({"statements": [s for s in STATEMENTS if ge <= s["statement_time"] < lt],
                       "next_page_token": ""})
    if path.startswith("/finance/202501/statements/"):
        return STMT_TXNS[path.split("/")[4]]
    if path.startswith("/finance/202501/orders/"):
        return ORDER_CALC[path.split("/")[4]]
    if path == tiktok_api.ORDER_SEARCH_PATH:
        return answer({"orders": ORDERS, "next_page_token": ""})
    if path == tiktok_api.ORDER_DETAIL_PATH:
        wanted = set(params[tiktok_api.ORDER_DETAIL_IDS_PARAM].split(","))
        return answer({"orders": [o for o in ORDERS if o["id"] in wanted]})
    if path == tiktok_api.INVENTORY_SEARCH_PATH:
        # The generated inventory.json is flat and predates any real answer. It is put into
        # the shape TikTok returned for My ShopEdge on 30 September 2026 (A32).
        wanted = json.loads(body)["product_ids"]
        grouped: dict[str, list] = {}
        for row in INVENTORY:
            if row["product_id"] in wanted:
                qty = STOCK_OVERRIDE.get(row["sku_id"], row["quantity"])
                grouped.setdefault(row["product_id"], []).append({
                    "id": row["sku_id"], "seller_sku": row["seller_sku"],
                    "total_available_inventory_distribution": {"in_shop_inventory": {"quantity": qty}},
                    "total_available_quantity": qty, "total_committed_quantity": 0,
                    "warehouse_inventory": [{"available_quantity": qty, "committed_quantity": 0,
                                             "warehouse_id": row["warehouse_id"]}]})
        return answer({"inventory": [{"product_id": k, "skus": v} for k, v in grouped.items()]})
    if path == tiktok_api.RETURN_SEARCH_PATH:
        # The generated returns carry a private `_skus` list. It is put where the sync reads
        # items from, which is itself unverified (tiktok_sync's docstring).
        out = [dict(r, return_line_items=[{"sku_id": s} for s in r["_skus"]]) for r in RETURNS]
        return answer({"return_orders": out, "next_page_token": ""})
    return {"code": 404, "message": f"no recorded answer for {method} {path}"}


def expected_ledger():
    rows = json.load(open(ROWS))
    by_cat = Counter()
    for e in rows["ledger_entries"]:
        if e.get("settlement_id") and e["category"] not in ("cost_of_goods_sold", "stock_written_off"):
            by_cat[e["category"]] += e["amount_minor"]
    return by_cat


def position(conn, shop, tiktok_sku):
    return conn.execute(
        "select p.tiktok_stock, p.adjusted_delta, p.on_shelf from stock_positions p "
        "join skus k on k.id = p.sku_id where p.shop_id = %s and k.tiktok_sku_id = %s",
        (shop, tiktok_sku)).fetchone()


def stock_checks(url, shop, now):
    """STK-8 (A4.1) on real rows: TC-STK-08, 09, 10 and 11."""
    sku = INVENTORY[0]["sku_id"]
    base = INVENTORY[0]["quantity"]

    def run(count, adjusted):
        with psycopg.connect(url) as conn:
            conn.execute("update stock_positions set adjusted_delta = %s where sku_id = "
                         "(select id from skus where shop_id = %s and tiktok_sku_id = %s)", (adjusted, shop, sku))
            before = position(conn, shop, sku)
        STOCK_OVERRIDE[sku] = count
        result = tiktok_sync.run_due(fake, now + timedelta(hours=2))
        with psycopg.connect(url) as conn:
            return before, position(conn, shop, sku), result

    # TC-STK-08: a resellable return added 1; the seller also puts it back in TikTok.
    before, after, _ = run(base + 1, 1)
    with psycopg.connect(url) as conn:
        moved = conn.execute("select count(*), sum(quantity) from stock_movements where shop_id = %s "
                             "and movement_type = 'adjustment_absorbed'", (shop,)).fetchone()
        told = conn.execute("select title, body from notifications where shop_id = %s and type = 'stock_absorbed'",
                            (shop,)).fetchall()
    check(after == (base + 1, 0, before[2]) and moved == (1, 1),
          f"TC-STK-08: a matching rise in TikTok is absorbed and on the shelf stays {before[2]}: {before} to {after}")
    check(len(told) == 1 and "1 unit" in told[0][0] and str(before[2]) in told[0][1],
          f"TC-STK-08: the seller is told, naming the product and the count: {told}")
    # TC-STK-09: a rise of 50 against an adjustment of 3. It is above the tolerance of 20,
    # so A4 treats it as a restock: nothing is absorbed and a discrepancy is raised.
    before, after, _ = run(base + 51, 3)
    with psycopg.connect(url) as conn:
        raised = conn.execute("select count(*) from discrepancies where shop_id = %s and entity_type = 'sku' "
                              "and field = 'tiktok_stock' and status = 'open'", (shop,)).fetchone()[0]
    check(after[1] == 3 and after[2] == base + 54 and raised == 1,
          f"TC-STK-10: a rise above the tolerance flows through and raises a discrepancy: {after}, {raised}")
    # A rise of 5 against an adjustment of 3: 3 are absorbed and 2 flow through (TC-STK-09's rule).
    before, after, _ = run(base + 56, 3)
    check(after[1] == 0 and after[2] == before[2] + 2,
          f"TC-STK-09: absorption stops at the adjustment and the rest flows through: {before} to {after}")
    # TC-STK-11: TikTok's count falls, which is ordinary selling.
    before, after, _ = run(base + 50, 2)
    check(after[1] == 2 and after[2] == base + 52, f"TC-STK-11: a fall is never absorbed: {before} to {after}")
    STOCK_OVERRIDE.clear()


def main():
    url = os.environ["DATABASE_URL"]
    shop_tt = SHOPS[0]
    with psycopg.connect(url) as conn:
        account = conn.execute(
            "insert into accounts (email, auth_subject, display_name) values "
            "('sync-check@example.test', 'stack|sync-check', 'Sync check') returning id").fetchone()[0]
        shop = conn.execute(
            "insert into shops (account_id, tiktok_shop_id, shop_name, region, seller_type, currency, "
            "connection_status) values (%s, %s, %s, 'GB', 'LOCAL', 'GBP', 'pending') returning id",
            (account, shop_tt["id"], shop_tt["name"])).fetchone()[0]
        conn.execute(
            "insert into tiktok_connections (shop_id, access_token_enc, refresh_token_enc, shop_cipher_enc, "
            "access_expires_at, refresh_expires_at, scopes) values (%s, %s, %s, %s, now() + interval '6 days', "
            "now() + interval '300 days', '{seller.finance.info,seller.order.info}')",
            (shop, _encrypt("old-access"), _encrypt("old-refresh"), _encrypt("cipher-x")))

    now = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
    first = tiktok_sync.run_due(fake, now)
    print(json.dumps(first, default=str))
    check(len(first) == 1 and "error" not in first[0], "one shop ran without an error")
    check(first[0].get("refresh") == "not_due", "a token with six days left is not refreshed")
    check(all(s == "completed" for s in (first[0].get("sync") or {}).values())
          and set(first[0].get("sync") or {}) == {"orders", "returns", "finance", "inventory"},
          f"orders, returns, finance and inventory completed: {first[0].get('sync')}")
    asked = [c for c in calls if c[1] == tiktok_api.INVENTORY_SEARCH_PATH]
    check(asked and all(c[0] == "POST" for c in asked), "Inventory Search is asked by POST, as it was live")
    fake_sku = set(fake("POST", tiktok_api.API_BASE + tiktok_api.INVENTORY_SEARCH_PATH, {}, {},
                        json.dumps({"product_ids": [INVENTORY[0]["product_id"]]}).encode())
                   ["data"]["inventory"][0]["skus"][0])
    live_sku = set(LIVE_INVENTORY["inventory"][0]["skus"][0])
    check(fake_sku == live_sku, f"the fake answers in the fields TikTok returned live: {sorted(live_sku ^ fake_sku)}")

    signed = all("sign" in p and "app_key" in p and len(p["timestamp"]) == 10 and p.get("shop_cipher") == "cipher-x"
                 for m, path, p in calls if path.startswith(("/finance", "/order", "/return")))
    check(signed, "every shop call is signed, carries a ten digit timestamp and the shop cipher")
    listings = [p for m, path, p in calls if tiktok_api._template(path) in tiktok_api.SORT_FIELDS]
    check(listings and all(p.get("sort_field") and p.get("sort_order") in ("ASC", "DESC") for p in listings),
          f"all {len(listings)} listing calls send sort_field and sort_order")

    with psycopg.connect(url) as conn:
        got = Counter(dict(conn.execute(
            "select category, sum(amount_minor)::bigint from ledger_entries where shop_id = %s group by category",
            (shop,)).fetchall()))
        want = expected_ledger()
        for cat in sorted(set(got) | set(want)):
            check(got.get(cat, 0) == want.get(cat, 0),
                  f"{cat}: the sync posted {got.get(cat, 0)}, rows.json holds {want.get(cat, 0)} settled")
        unsettled = conn.execute("select count(*) from ledger_entries where shop_id = %s and settlement_id is null",
                                 (shop,)).fetchone()[0]
        check(unsettled == 0, "every entry the sync posted carries its settlement (the owner's ruling)")
        off = conn.execute(
            "select s.tiktok_statement_id from settlements s join ledger_entries le on le.settlement_id = s.id "
            "where s.shop_id = %s group by s.tiktok_statement_id "
            "having sum(le.amount_minor) filter (where le.entry_type not in ('reserve')) <> 0", (shop,)).fetchall()
        check(off == [], f"each payout is the negative of its statement's own entries: {off}")
        n = conn.execute("select (select count(*) from settlements where shop_id = %(s)s), "
                         "(select count(*) from orders where shop_id = %(s)s), "
                         "(select count(*) from returns where shop_id = %(s)s), "
                         "(select count(*) from ledger_entries where shop_id = %(s)s)", {"s": shop}).fetchone()
        check(n[0] == len(STATEMENTS), f"{n[0]} settlements for {len(STATEMENTS)} statements")
        check(n[1] == len(ORDERS), f"{n[1]} orders for {len(ORDERS)} in the payload")
        check(n[2] == len(RETURNS), f"{n[2]} returns for {len(RETURNS)} in the payload")
        months = conn.execute(
            "select count(*) from ledger_entries le join settlements s on s.id = le.settlement_id "
            "where le.shop_id = %s and le.settlement_month <> date_trunc('month', "
            "s.statement_time at time zone 'Europe/London')::date", (shop,)).fetchone()[0]
        check(months == 0, "every entry's settlement month is its statement's London month")
        entries_before = n[3]
        sold = {r[0] for r in conn.execute(
            "select distinct k.tiktok_sku_id from order_lines l join skus k on k.id = l.sku_id "
            "where l.shop_id = %s", (shop,)).fetchall()}
        stock = dict(conn.execute(
            "select k.tiktok_sku_id, p.tiktok_stock from stock_positions p join skus k on k.id = p.sku_id "
            "where p.shop_id = %s", (shop,)).fetchall())
        given = {r["sku_id"]: r["quantity"] for r in INVENTORY}
        check(set(stock) == sold and all(stock[k] == given[k] for k in stock),
              f"every variant sold has TikTok's own count, {len(stock)} of {len(sold)}")

    calls.clear()
    second = tiktok_sync.run_due(fake, now + timedelta(hours=1))
    with psycopg.connect(url) as conn:
        after = conn.execute("select count(*) from ledger_entries where shop_id = %s", (shop,)).fetchone()[0]
        runs = conn.execute("select kind, count(*) from sync_runs where shop_id = %s group by kind order by kind",
                            (shop,)).fetchall()
    check(after == entries_before, f"a second run writes no ledger entry: {entries_before} then {after}")
    check("error" not in second[0], "the second run ran without an error")
    check(dict(runs) == {"backfill": 4, "incremental": 4}, f"the first run is a backfill, the second incremental: {runs}")
    cal = [p for m, path, p in calls if path == tiktok_api.STATEMENTS_PATH][0]
    stock_checks(url, shop, now)
    check(int(cal["statement_time_ge"]) == int((now - timedelta(days=3)).timestamp()),
          "the incremental run starts three days before the last one ended")

    # The refresh: two days or fewer left. A second shop from the same authorisation (A31.7)
    # shares the tokens and `authorised_at`; it is Indonesian, so the sync never reads it,
    # and a successful refresh must still hand it the new tokens.
    with psycopg.connect(url) as conn:
        conn.execute("update tiktok_connections set access_expires_at = %s where shop_id = %s",
                     (now + timedelta(days=1), shop))
        sibling = conn.execute(
            "insert into shops (account_id, tiktok_shop_id, shop_name, region, seller_type, currency, "
            "connection_status) values (%s, 'sibling-1', 'Sibling', 'ID', 'LOCAL', 'IDR', 'pending') "
            "returning id", (account,)).fetchone()[0]
        conn.execute(
            "insert into tiktok_connections (shop_id, access_token_enc, refresh_token_enc, shop_cipher_enc, "
            "access_expires_at, refresh_expires_at, scopes, authorised_at) select %s, access_token_enc, "
            "refresh_token_enc, %s, access_expires_at, refresh_expires_at, scopes, authorised_at "
            "from tiktok_connections where shop_id = %s", (sibling, _encrypt("cipher-y"), shop))
    os.environ["_CHECK_REFUSE_REFRESH"] = "1"
    refused = tiktok_sync.run_due(fake, now)
    with psycopg.connect(url) as conn:
        code, token = conn.execute("select refresh_failure_code, access_token_enc from tiktok_connections "
                                   "where shop_id = %s", (shop,)).fetchone()
    check(refused[0].get("refresh") == "failed" and code == "36004001", f"a refused refresh records TikTok's code: {code}")
    check(tiktok_api.decrypt(token) == "old-access", "a refused refresh leaves the stored token as it was")
    del os.environ["_CHECK_REFUSE_REFRESH"]
    refreshed = tiktok_sync.run_due(fake, now)
    with psycopg.connect(url) as conn:
        row = conn.execute("select access_token_enc, refresh_token_enc, access_expires_at, refresh_failure_code, "
                           "refresh_succeeded_at from tiktok_connections where shop_id = %s", (shop,)).fetchone()
    check(refreshed[0].get("refresh") == "refreshed", "a token with one day left is refreshed")
    check(tiktok_api.decrypt(row[0]) == "new-access" and tiktok_api.decrypt(row[1]) == "new-refresh",
          "the new tokens are stored encrypted and decrypt to what TikTok returned")
    check(row[2] == datetime.fromtimestamp(NEW_ACCESS_EXPIRES, timezone.utc) and row[3] is None and row[4] == now,
          "the new expiry is the instant TikTok gave, and the failure is cleared")
    check(b"new-access" not in bytes(row[0]), "the stored token is not the token in the clear")
    with psycopg.connect(url) as conn:
        sib = conn.execute("select access_token_enc, shop_cipher_enc, access_expires_at from tiktok_connections "
                           "where shop_id = %s", (sibling,)).fetchone()
    check(tiktok_api.decrypt(sib[0]) == "new-access" and tiktok_api.decrypt(sib[1]) == "cipher-y"
          and sib[2] == row[2], "the refresh hands the new tokens to the shop sharing its authorisation")

    print(f"{ok} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
