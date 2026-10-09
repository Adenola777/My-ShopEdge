"""Checks the order count against the plan's limit (A16.3), added 9 October 2026.

    createdb mse_usage
    DATABASE_URL=... python3 service/scripts/migrate.py
    DATABASE_URL=... python3 testdata/order_usage_check.py

It needs a database built from empty by `migrate.py`, as `tiktok_sync_check.py` does, and it
answers every TikTok request through that script's stand-in, so nothing reaches TikTok. Rows
are written as the connecting role (the migrator, as the other checks do) and read back as the
service reads them, through `db.tenant()` as `mse_app` under row level security. Drop the
database afterwards.

What it checks:
- Below 80 per cent, at 80, at 99 and at 100 per cent of a Starter trial, with the larger plan.
- The billing period's edges: an order at its start counts, one a second before does not, one
  a second before its end counts, and one at its end does not. The period crosses the end of
  British Summer Time on 25 October 2026.
- A cancelled order counts.
- The notice at 100 per cent is written once per period, not below it, and again in the next.
- An account with no subscription, an incomplete or cancelled one, one with no period, and one
  whose period has ended get no usage and no notice.
- One account's orders never reach another account's count.
- The limit is the account's: orders on two shops of one account are counted together, and the
  real sync (`run_one` with the stand-in) writes the notice when its orders reach the limit, and
  writes no second one on the next read.
- GET /shops/{shopId}/today serves `order_usage` from the real database.

**Run on 9 October 2026** against databases built from empty by `migrate.py`: every check
passed with `payloads` and with `payloads_year`.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tiktok_sync_check as stand_in  # noqa: E402  sets the TikTok variables and the path

import psycopg  # noqa: E402

from app import db, tiktok_sync  # noqa: E402
from app.connections import _encrypt  # noqa: E402
from app.order_usage import notify_order_limit, read_order_usage  # noqa: E402

ok = bad = 0
UTC = timezone.utc
# Starts at 10:30 London in BST and ends at 10:30 London in GMT, so it spans 25 October.
START = datetime(2026, 10, 1, 9, 30, tzinfo=UTC)
END = datetime(2026, 11, 1, 10, 30, tzinfo=UTC)
NOW = datetime(2026, 10, 15, 12, tzinfo=UTC)
SECOND = timedelta(seconds=1)


def check(cond, what):
    global ok, bad
    print(("PASS " if cond else "FAIL ") + what)
    ok += bool(cond)
    bad += not cond


def new_account(conn, n):
    return conn.execute(
        "insert into accounts (email, auth_subject, display_name) values (%s, %s, 'Usage') "
        "returning id", (f"usage-{n}@example.test", f"stack|usage-{n}")).fetchone()[0]


def new_shop(conn, account, n, status="connected"):
    return conn.execute(
        "insert into shops (account_id, tiktok_shop_id, shop_name, region, seller_type, currency, "
        "connection_status) values (%s, %s, %s, 'GB', 'LOCAL', 'GBP', %s) returning id",
        (account, f"usage-shop-{n}", f"Usage shop {n}", status)).fetchone()[0]


def subscribe(conn, account, n, plan="starter", status="trialing", start=START, end=END):
    conn.execute(
        "insert into subscriptions (account_id, plan_slug, status, stripe_customer_id, trial_end, "
        "current_period_start, current_period_end) values (%s, %s, %s, %s, %s, %s, %s)",
        (account, plan, status, f"cus_usage_{n}", end if status == "trialing" else None, start, end))


serial = 0


def add_orders(conn, shop, times, status="COMPLETED"):
    global serial
    for t in times:
        serial += 1
        conn.execute(
            "insert into orders (shop_id, tiktok_order_id, status, order_created_at, gross_minor) "
            "values (%s, %s, %s, %s, 800)", (shop, f"usage-{serial}", status, t))


def inside(n, base=START + timedelta(days=1)):
    return [base + timedelta(minutes=i) for i in range(n)]


def usage(account, now=NOW):
    with db.tenant(account) as conn:
        return read_order_usage(conn, account, now)


def notify(account, now=NOW):
    with db.tenant(account) as conn:
        return notify_order_limit(conn, account, now)


def notices(url, account):
    with psycopg.connect(url) as conn:
        return conn.execute(
            "select shop_id, type, severity, title, body, dedupe_key from notifications "
            "where account_id = %s and type = 'order_limit_passed' order by created_at", (account,)).fetchall()


def main():
    url = os.environ["DATABASE_URL"]

    # --- one account, one shop, a Starter trial -------------------------------------------
    with psycopg.connect(url) as conn:
        a = new_account(conn, 1)
        shop = new_shop(conn, a, 1)
        subscribe(conn, a, 1)
        # The edges: two outside the period, two inside it.
        add_orders(conn, shop, [START - SECOND, START, END - SECOND, END])
        # 75 more inside, ten of them cancelled, so 77 count.
        add_orders(conn, shop, inside(65))
        add_orders(conn, shop, inside(10, START + timedelta(days=2)), status="CANCELLED")

    u = usage(a)
    print("77 in the period:", u)
    check(u is not None and u.order_count == 77,
          "the period counts its start and the second before its end, not the second before its "
          "start or its end, and cancelled orders count")
    check(u.state == "below" and u.order_limit == 100 and u.plan == "starter"
          and u.plan_name == "Starter", "77 of 100 on Starter is below")
    check(u.larger_plan is not None and u.larger_plan.slug == "growth"
          and u.larger_plan.order_limit == 500, "the larger plan offered is Growth at 500")
    check(u.period_start == START and u.period_end == END, "the period is the subscription's")
    check(not notify(a) and notices(url, a) == [], "no notice below the limit")

    with psycopg.connect(url) as conn:
        add_orders(conn, shop, inside(2, START + timedelta(days=3)))
    u = usage(a)
    check(u.order_count == 79 and u.state == "below", "79 of 100 is below")

    with psycopg.connect(url) as conn:
        add_orders(conn, shop, inside(1, START + timedelta(days=4)))
    u = usage(a)
    check(u.order_count == 80 and u.state == "approaching", "80 of 100 is approaching")

    with psycopg.connect(url) as conn:
        add_orders(conn, shop, inside(19, START + timedelta(days=5)))
    u = usage(a)
    check(u.order_count == 99 and u.state == "approaching", "99 of 100 is approaching")
    check(not notify(a) and notices(url, a) == [], "no notice at 99")

    with psycopg.connect(url) as conn:
        add_orders(conn, shop, inside(1, START + timedelta(days=6)))
    u = usage(a)
    check(u.order_count == 100 and u.state == "passed", "100 of 100 is passed")
    check(notify(a), "the notice is written at 100")
    check(not notify(a) and not notify(a, NOW + timedelta(days=5)),
          "a second and third run in the same period write nothing")
    n = notices(url, a)
    print("notice:", n)
    check(len(n) == 1 and n[0][0] is None and n[0][2] == "warning"
          and n[0][5] == f"order_limit_passed:{a}:{START.isoformat()}",
          "one warning notice for the account, with no shop, keyed on the account and period")
    check("reached the Starter plan's limit of 100 orders" in n[0][3]
          and "1 November 2026" in n[0][4] and "The Growth plan covers up to 500 orders a month."
          in n[0][4] and "—" not in n[0][3] + n[0][4] and "–" not in n[0][3] + n[0][4],
          "the notice names the limit, the London end of the period and the larger plan, with no dash")

    # --- the next period ------------------------------------------------------------------
    nxt_end = END + timedelta(days=30)
    with psycopg.connect(url) as conn:
        conn.execute("update subscriptions set status = 'active', current_period_start = %s, "
                     "current_period_end = %s where account_id = %s", (END, nxt_end, a))
    later = END + timedelta(days=3)
    u = usage(a, later)
    check(u.order_count == 1 and u.state == "below",
          "the next period starts again, holding only the order at its start")
    with psycopg.connect(url) as conn:
        add_orders(conn, shop, inside(110, END + timedelta(days=1)))
    u = usage(a, later)
    check(u.order_count == 111 and u.state == "passed", "111 of 100 in the next period is passed")
    check(notify(a, later), "the next period writes its own notice")
    n = notices(url, a)
    check(len(n) == 2 and n[1][5] == f"order_limit_passed:{a}:{END.isoformat()}"
          and "passed the Starter plan's limit" in n[1][3] and "111 orders" in n[1][4],
          "two notices in all, the second saying passed with the count")
    check(usage(a, nxt_end) is None, "a period that has ended serves nothing")

    # --- accounts that get nothing ------------------------------------------------------------
    with psycopg.connect(url) as conn:
        b = new_account(conn, 2)          # no subscription
        bshop = new_shop(conn, b, 2)
        add_orders(conn, bshop, inside(150))
        c = new_account(conn, 3)          # incomplete
        subscribe(conn, c, 3, status="incomplete")
        add_orders(conn, new_shop(conn, c, 3), inside(150))
        d = new_account(conn, 4)          # cancelled
        subscribe(conn, d, 4, status="canceled")
        add_orders(conn, new_shop(conn, d, 4), inside(150))
        e = new_account(conn, 5)          # trialing with no period recorded
        subscribe(conn, e, 5, start=None, end=None)
        add_orders(conn, new_shop(conn, e, 5), inside(150))
    for who, what in ((b, "no subscription"), (c, "an incomplete subscription"),
                      (d, "a cancelled subscription"), (e, "no period")):
        check(usage(who) is None and not notify(who) and notices(url, who) == [],
              f"{what}: no usage and no notice")

    # --- tenancy: B's 150 orders are not in A's count, and A cannot see B's --------------------
    u = usage(a, later)
    check(u.order_count == 111, "another account's orders never reach this account's count")
    with db.tenant(b) as conn:
        seen = conn.execute("select count(*) from order_quota").fetchone()[0]
    check(seen == 0, "an account with no subscription reads no row of order_quota")

    # --- two shops, and the real sync ------------------------------------------------------
    # The stand-in's orders are dated July and August 2026. The period below holds every one
    # created from 1 August, so the sync's own orders bring the count to the limit.
    p_start = datetime(2026, 8, 1, tzinfo=UTC)
    p_end = datetime(2026, 9, 1, tzinfo=UTC)
    sync_now = datetime(2026, 8, 25, 12, tzinfo=UTC)
    from_sync = sum(1 for o in stand_in.ORDERS
                    if p_start <= datetime.fromtimestamp(o["create_time"], UTC) < p_end)
    print("orders the stand-in holds in the period:", from_sync)
    with psycopg.connect(url) as conn:
        f = new_account(conn, 6)
        subscribe(conn, f, 6, start=p_start, end=p_end)
        synced = new_shop(conn, f, 6, status="pending")
        conn.execute(
            "insert into tiktok_connections (shop_id, access_token_enc, refresh_token_enc, "
            "shop_cipher_enc, access_expires_at, refresh_expires_at, scopes) values (%s, %s, %s, "
            "%s, %s, %s, '{seller.finance.info,seller.order.info}')",
            (synced, _encrypt("access"), _encrypt("refresh"), _encrypt("cipher-x"),
             sync_now + timedelta(days=6), sync_now + timedelta(days=300)))
        other = new_shop(conn, f, 7)
        add_orders(conn, other, inside(100 - from_sync - 1, p_start + timedelta(days=1)))
    u = usage(f, sync_now)
    check(u.order_count == 100 - from_sync - 1 and u.state == "approaching",
          "before the sync the second shop's orders alone are counted")

    result = tiktok_sync.run_one(synced, f, stand_in.fake, sync_now)
    print("first sync:", result)
    u = usage(f, sync_now)
    check(u.order_count == 99, "the account's count covers both shops: 99 after the sync")
    check(notices(url, f) == [], "the sync writes no notice at 99")

    with psycopg.connect(url) as conn:
        add_orders(conn, other, inside(1, p_start + timedelta(days=10)))
    result = tiktok_sync.run_one(synced, f, stand_in.fake, sync_now + timedelta(hours=1))
    print("second sync:", result)
    n = notices(url, f)
    print("notice from the sync:", n)
    check(all(s in ("completed", "partial") for s in result.get("sync", {}).values())
          and "error" not in result, "the sync carries on at the limit")
    check(len(n) == 1 and n[0][5] == f"order_limit_passed:{f}:{p_start.isoformat()}",
          "the sync writes the notice once the account reaches 100")
    tiktok_sync.run_one(synced, f, stand_in.fake, sync_now + timedelta(hours=2))
    check(len(notices(url, f)) == 1, "the next sync writes no second notice")

    # --- Today, served from this database -----------------------------------------------------
    from fastapi.testclient import TestClient

    from app import today_view
    from app.auth import Account, require_account
    from app.main import app
    from app.shops import require_shop

    today_view.now_utc = lambda: sync_now
    app.dependency_overrides[require_account] = lambda: Account(
        id=UUID(str(f)), email="usage-6@example.test", name="Usage", subject="stack|usage-6")
    app.dependency_overrides[require_shop] = lambda: UUID(str(other))
    r = TestClient(app).get(f"/v1/shops/{other}/today")
    body = r.json() if r.status_code == 200 else {}
    print("today:", r.status_code, body.get("order_usage"))
    ou = body.get("order_usage") or {}
    check(r.status_code == 200 and ou.get("state") == "passed" and ou.get("order_count") == 100
          and ou.get("order_limit") == 100 and ou.get("plan_name") == "Starter"
          and (ou.get("larger_plan") or {}).get("name") == "Growth",
          "GET today serves the account's usage on the second shop's page")
    app.dependency_overrides[require_account] = lambda: Account(
        id=UUID(str(b)), email="usage-2@example.test", name="Usage", subject="stack|usage-2")
    app.dependency_overrides[require_shop] = lambda: UUID(str(bshop))
    r = TestClient(app).get(f"/v1/shops/{bshop}/today")
    check(r.status_code == 200 and r.json().get("order_usage") is None,
          "GET today serves null to an account with no subscription")

    print(f"{ok} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
