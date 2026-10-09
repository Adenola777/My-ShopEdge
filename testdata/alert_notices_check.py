"""Checks the low stock and return check notices (service/app/alert_notices.py), added
9 October 2026.

    createdb mse_alerts
    DATABASE_URL=... python3 service/scripts/migrate.py
    DATABASE_URL=... python3 testdata/alert_notices_check.py

It needs a database built from empty by `migrate.py`, as `tiktok_sync_check.py` does, and it
answers every TikTok request through that script's stand-in, so nothing reaches TikTok. Each
evaluation runs through the daily read, `tiktok_sync.run_due`, as production runs it.

Two things are set by hand, because the stand-in cannot give them:
- One order, dated yesterday on the real clock and unknown to the stand-in, sells 14 units of
  one variant, so its pace is one a day and its days of cover equal its stock on hand. Days of
  cover reads the real London day (`stock.positions`), and every payload order is older than
  fourteen days.
- TikTok's count for that variant is moved through the stand-in's `STOCK_OVERRIDE`.

Return reminders are measured to the read's `until`, so the clock is moved by passing a later
`now` to `run_due`; each pending item was written at the real time of the first read.

What it checks:
- A variant below the threshold raises one warning notice naming it, linked to the SKU.
- A second read raises no second notice.
- Lowering the threshold so the variant is no longer low clears the notice, and raising it
  again takes effect on the next read with one new notice.
- A variant that recovers through a restock is cleared, and one notice is raised when it
  drops again.
- A notice the seller marked done is not raised again after a threshold change while the
  variant stays low, nor when it runs out and comes back to low.
- A read whose stock step failed neither raises nor clears a low stock notice.
- A return inside the window raises nothing, a changed window is applied, a return past the
  window raises one notice, and a later read raises no second.
- A return checked before the window ends raises none, a return checked after its reminder
  clears the reminder, and a cancellation or refund with nothing coming back raises none.

**Run on 9 October 2026** against databases built from empty by `migrate.py`: 26 of 26 passed
on `payloads` with `rows.json`, and 26 of 26 on `payloads_year` with `rows_year.json`.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tiktok_sync_check as stand_in  # noqa: E402  sets the TikTok variables and the path

import psycopg  # noqa: E402

from app import returns, tiktok_sync  # noqa: E402
from app.connections import _encrypt  # noqa: E402

ok = bad = 0
NOW = datetime.now(timezone.utc).replace(microsecond=0)


def check(cond, what):
    global ok, bad
    print(("PASS " if cond else "FAIL ") + what)
    ok += bool(cond)
    bad += not cond


def dashless(text):
    return "—" not in text and "–" not in text


def setup(url):
    with psycopg.connect(url) as conn:
        account = conn.execute(
            "insert into accounts (email, auth_subject, display_name) values "
            "('alerts@example.test', 'stack|alerts', 'Alerts') returning id").fetchone()[0]
        shop = conn.execute(
            "insert into shops (account_id, tiktok_shop_id, shop_name, region, seller_type, currency, "
            "connection_status) values (%s, %s, 'Alert shop', 'GB', 'LOCAL', 'GBP', 'pending') returning id",
            (account, stand_in.SHOPS[0]["id"])).fetchone()[0]
        conn.execute(
            "insert into tiktok_connections (shop_id, access_token_enc, refresh_token_enc, shop_cipher_enc, "
            "access_expires_at, refresh_expires_at, scopes) values (%s, %s, %s, %s, now() + interval '30 days', "
            "now() + interval '300 days', '{seller.finance.info,seller.order.info}')",
            (shop, _encrypt("access"), _encrypt("refresh"), _encrypt("cipher-x")))
    return account, shop


def read(at=NOW, transport=None):
    result = tiktok_sync.run_due(transport or stand_in.fake, at)
    assert len(result) == 1 and "error" not in result[0], result
    return result[0]


def settings(url, shop, low=14, back=7):
    with psycopg.connect(url) as conn:
        conn.execute(
            "insert into alert_settings (shop_id, low_stock_days, coming_back_days) values (%s, %s, %s) "
            "on conflict (shop_id) do update set low_stock_days = excluded.low_stock_days, "
            "coming_back_days = excluded.coming_back_days, updated_at = now()", (shop, low, back))


def notices(url, shop, kind):
    with psycopg.connect(url) as conn:
        return conn.execute(
            "select id, status, severity, title, body, entity_type, entity_id, dedupe_key from notifications "
            "where shop_id = %s and type = %s order by created_at, id", (shop, kind)).fetchall()


def mark_done(url, notice_id):
    with psycopg.connect(url) as conn:
        conn.execute("update notifications set status = 'done' where id = %s", (notice_id,))


def stock_checks(url, account, shop):
    tiktok_sku = stand_in.INVENTORY[0]["sku_id"]
    with psycopg.connect(url) as conn:
        sku = conn.execute("select id from skus where shop_id = %s and tiktok_sku_id = %s",
                           (shop, tiktok_sku)).fetchone()[0]
        order = conn.execute(
            "insert into orders (shop_id, tiktok_order_id, status, order_created_at, gross_minor) "
            "values (%s, 'alert-check-pace', 'COMPLETED', %s, 1400) returning id", (shop, NOW - timedelta(days=1))).fetchone()[0]
        conn.execute(
            "insert into order_lines (shop_id, order_id, sku_id, tiktok_line_id, quantity, unit_price_minor) "
            "values (%s, %s, %s, 'alert-check-line', 14, 100)", (shop, order, sku))

    def at(count, low=14):
        stand_in.STOCK_OVERRIDE[tiktok_sku] = count
        settings(url, shop, low=low)
        read()
        return notices(url, shop, "low_stock")

    def is_open(n):
        return n[1] != "done" and n[7] == f"low_stock:{sku}"

    got = at(5)
    print("first low stock notice:", got)
    check(len(got) == 1 and is_open(got[0]) and got[0][2] == "warning" and got[0][5] == "sku" and got[0][6] == sku,
          "a variant with 5 days of cover against 14 raises one warning notice on the SKU")
    check(got and got[0][3].endswith("is low on stock.") and "5 units on hand" in got[0][4]
          and "5 days of cover" in got[0][4] and "threshold is 14 days" in got[0][4]
          and dashless(got[0][3] + got[0][4]), "the notice names the variant, its figures and the threshold")
    got = at(5)
    check(len(got) == 1 and is_open(got[0]), "a second read raises no second notice")

    got = at(5, low=3)
    check(len(got) == 1 and got[0][1] == "done" and got[0][7] == f"low_stock:{sku}:cleared:{got[0][0]}",
          "lowering the threshold below the cover clears the notice and frees its key")
    got = at(5, low=14)
    check(len(got) == 2 and is_open(got[1]),
          "raising the threshold again takes effect on the next read with one new notice")

    got = at(100)
    check(len(got) == 2 and all(n[1] == "done" for n in got), "a restock to 100 days of cover clears the notice")
    got = at(100)
    check(len(got) == 2, "a healthy variant raises nothing")
    got = at(5)
    check(len(got) == 3 and is_open(got[2]), "a variant that recovered and dropped again is told once more")

    mark_done(url, got[2][0])
    got = at(5, low=10)
    check(len(got) == 3 and got[2][1] == "done" and got[2][7] == f"low_stock:{sku}",
          "a notice the seller marked done is not raised again after a threshold change while still low")
    got = at(0)
    check(len(got) == 3, "running out raises no low stock notice and does not end the spell")
    got = at(5)
    check(len(got) == 3, "coming back from out to low is the same spell, so nothing is raised")

    def no_stock(method, u, params, headers, body):
        if "/product/" in u:
            return {"code": 1234, "message": "refused by the check"}
        return stand_in.fake(method, u, params, headers, body)

    stand_in.STOCK_OVERRIDE[tiktok_sku] = 100
    settings(url, shop, low=3)
    result = read(transport=no_stock)
    got = notices(url, shop, "low_stock")
    check(result["sync"].get("inventory") == "failed" and got[2][7] == f"low_stock:{sku}",
          f"a read whose stock step failed does not clear the notice: {result['sync']}")
    stand_in.STOCK_OVERRIDE.clear()
    settings(url, shop)


def item_ids(url, shop, tiktok_return):
    with psycopg.connect(url) as conn:
        return [r[0] for r in conn.execute(
            "select ri.id from return_items ri join returns r on r.id = ri.return_id "
            "where r.shop_id = %s and r.tiktok_return_id = %s and ri.seller_check_status = 'pending'",
            (shop, tiktok_return)).fetchall()]


def check_item(account, shop, item):
    returns.check_return_item(
        returns.CheckIn(seller_check_status="resellable"), SimpleNamespace(id=account), shop, item, None)


def return_checks(url, account, shop):
    with psycopg.connect(url) as conn:
        by_kind = conn.execute(
            "select r.tiktok_return_id, r.id, r.kind, bool_or(ri.seller_check_status = 'pending') "
            "from returns r left join return_items ri on ri.return_id = r.id where r.shop_id = %s "
            "group by r.tiktok_return_id, r.id, r.kind order by r.tiktok_return_id", (shop,)).fetchall()
    waiting = [r for r in by_kind if r[3]]
    others = [r for r in by_kind if not r[3]]
    print("returns:", [(r[0], r[2], r[3]) for r in by_kind])
    check(len(waiting) >= 2 and all(r[2] == "return_refund" for r in waiting)
          and {r[2] for r in others} >= {"cancellation", "refund_only"},
          f"{len(waiting)} returns wait for a check, and the cancellation and refund only do not")

    first, second = waiting[0], waiting[1]
    for item in item_ids(url, shop, first[0]):
        check_item(account, shop, item)

    read(NOW + timedelta(days=6))
    check(notices(url, shop, "return_unchecked") == [], "a return six days into a seven day window raises nothing")
    settings(url, shop, back=10)
    read(NOW + timedelta(days=8))
    check(notices(url, shop, "return_unchecked") == [], "with the window changed to ten days, day eight raises nothing")
    settings(url, shop, back=7)
    read(NOW + timedelta(days=8))
    got = notices(url, shop, "return_unchecked")
    print("return notices:", got)
    told = {str(n[6]) for n in got}
    check(len(got) == len(waiting) - 1 and told == {str(r[1]) for r in waiting[1:]},
          "with the window back at seven days, day eight raises one notice for each return still waiting")
    check(str(first[1]) not in told, "a return checked inside the window raises none")
    check(not told & {str(r[1]) for r in others}, "a cancellation and a refund with nothing coming back raise none")
    check(all(n[1] == "unread" and n[2] == "warning" and n[5] == "return" and n[7] == f"return_unchecked:{n[6]}"
              for n in got), "each is an unread warning on the return, keyed by the return")
    check(got and "has waited more than 7 days for your check." in got[0][3] and "Check returns" in got[0][4]
          and "first read this return from TikTok on" in got[0][4] and all(dashless(n[3] + n[4]) for n in got),
          "the wording names the order, the window and what to do, with no dash")

    read(NOW + timedelta(days=9))
    check(len(notices(url, shop, "return_unchecked")) == len(got), "a later read raises no second notice")

    for item in item_ids(url, shop, second[0]):
        check_item(account, shop, item)
    read(NOW + timedelta(days=9))
    after = {str(n[6]): n[1] for n in notices(url, shop, "return_unchecked")}
    check(after[str(second[1])] == "done" and sum(s != "done" for s in after.values()) == len(got) - 1,
          "a return checked after its reminder clears that reminder and no other")
    read(NOW + timedelta(days=10))
    check(len(notices(url, shop, "return_unchecked")) == len(got), "a cleared reminder is not raised again")


def main():
    url = os.environ["DATABASE_URL"]
    account, shop = setup(url)
    first = read()
    print("first read:", first)
    check(set(first["sync"].values()) == {"completed"}, "the first read completed every domain")
    check(notices(url, shop, "return_unchecked") == [], "the first read raises no return reminder")
    stock_checks(url, account, shop)
    return_checks(url, account, shop)
    with psycopg.connect(url) as conn:
        runs = conn.execute("select distinct domain from sync_runs where shop_id = %s", (shop,)).fetchall()
    check({r[0] for r in runs} == {"orders", "returns", "finance", "inventory"},
          "the notices write no sync_runs row of their own")
    print(f"{ok} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
