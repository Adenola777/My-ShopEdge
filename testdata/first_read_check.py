"""Checks the notice a shop's first read leaves, added 9 October 2026.

    createdb mse_first_read
    DATABASE_URL=... python3 service/scripts/migrate.py
    DATABASE_URL=... python3 testdata/first_read_check.py

It needs a database built from empty by `migrate.py`, as `tiktok_sync_check.py` does, and it
answers every TikTok request through that script's stand-in, so nothing reaches TikTok. The
ledger is append-only, so the rows it writes are removed by dropping the database afterwards.

What it checks:
- The first read after a connection (connections._first_sync) leaves one
  `first_read_complete` notice, and the ledger still equals the settled part of `rows.json`.
- A second first read and a daily read leave no other notice and no new entry.
- A partial first read says so in its notice. A failed first read leaves none.

**Run on 9 October 2026** against a database built from empty by `migrate.py`: every check
passed on `payloads` with `rows.json`.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tiktok_sync_check as stand_in  # noqa: E402  sets the TikTok variables and the path

import psycopg  # noqa: E402

from app import connections, tiktok_sync  # noqa: E402
from app.connections import _encrypt  # noqa: E402

ok = bad = 0
NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
OFF_BY = "202608A-0001"   # the statement the partial read is refused


def check(cond, what):
    global ok, bad
    print(("PASS " if cond else "FAIL ") + what)
    ok += bool(cond)
    bad += not cond


def new_shop(url, n):
    with psycopg.connect(url) as conn:
        account = conn.execute(
            "insert into accounts (email, auth_subject, display_name) values (%s, %s, 'First read') "
            "returning id", (f"first-read-{n}@example.test", f"stack|first-read-{n}")).fetchone()[0]
        shop = conn.execute(
            "insert into shops (account_id, tiktok_shop_id, shop_name, region, seller_type, currency, "
            "connection_status) values (%s, %s, %s, 'GB', 'LOCAL', 'GBP', 'pending') returning id",
            (account, f"first-read-{n}", f"Check shop {n}")).fetchone()[0]
        conn.execute(
            "insert into tiktok_connections (shop_id, access_token_enc, refresh_token_enc, shop_cipher_enc, "
            "access_expires_at, refresh_expires_at, scopes) values (%s, %s, %s, %s, now() + interval '6 days', "
            "now() + interval '300 days', '{seller.finance.info,seller.order.info}')",
            (shop, _encrypt("access"), _encrypt("refresh"), _encrypt("cipher-x")))
    return account, shop


def first_read(account, shop, transport, now=NOW):
    """connections._first_sync as the callback runs it, with the stand-in for TikTok."""
    real = tiktok_sync.run_one
    tiktok_sync.run_one = lambda s, a: real(s, a, transport, now)
    try:
        connections._first_sync(shop, account)
    finally:
        tiktok_sync.run_one = real


def counts(url, shop):
    with psycopg.connect(url) as conn:
        return conn.execute(
            "select (select count(*) from notifications where shop_id = %(s)s and type = 'first_read_complete'), "
            "(select count(*) from ledger_entries where shop_id = %(s)s)", {"s": shop}).fetchone()


def main():
    url = os.environ["DATABASE_URL"]
    account, shop = new_shop(url, 1)

    first_read(account, shop, stand_in.fake)
    with psycopg.connect(url) as conn:
        ledger = dict(conn.execute(
            "select category, sum(amount_minor)::bigint from ledger_entries where shop_id = %s "
            "group by category", (shop,)).fetchall())
        notices = conn.execute(
            "select severity, title, body, entity_type, entity_id, dedupe_key from notifications "
            "where shop_id = %s and type = 'first_read_complete'", (shop,)).fetchall()
    print("notice:", notices)
    want = stand_in.expected_ledger()
    check(all(ledger.get(c, 0) == want.get(c, 0) for c in set(ledger) | set(want)),
          "the ledger equals the settled part of rows.json")
    check(len(notices) == 1 and notices[0][0] == "info" and notices[0][3] == "shop"
          and notices[0][4] == shop and notices[0][5] == f"first_read_complete:{shop}",
          "one info notice on the shop after the first read")
    check(notices and "Check shop 1" in notices[0][1] and "could not be read" not in notices[0][2]
          and "\u2014" not in notices[0][2] and "\u2013" not in notices[0][2],
          "a completed read names the shop, says nothing of a partial read and has no dash")

    before = counts(url, shop)
    first_read(account, shop, stand_in.fake, NOW + timedelta(hours=1))
    tiktok_sync.run_due(stand_in.fake, NOW + timedelta(hours=2))
    after = counts(url, shop)
    print("before and after a second first read and a daily read:", before, after)
    check(after == before and before[0] == 1, "no second notice and no new entry")

    # A partial first read: one statement's transactions are refused.
    account2, shop2 = new_shop(url, 2)

    def partial(method, u, params, headers, body):
        if f"/statements/{OFF_BY}/" in u:
            return {"code": 1234, "message": "refused by the check"}
        return stand_in.fake(method, u, params, headers, body)

    first_read(account2, shop2, partial)
    with psycopg.connect(url) as conn:
        p = conn.execute("select body from notifications where shop_id = %s and type = 'first_read_complete'",
                         (shop2,)).fetchall()
    print("partial notice:", p)
    check(len(p) == 1 and "Some records could not be read this time." in p[0][0],
          "a partial first read leaves one notice that says so")

    # A failed first read: every order search is refused.
    account3, shop3 = new_shop(url, 3)

    def failing(method, u, params, headers, body):
        if "/order/" in u:
            return {"code": 1234, "message": "refused by the check"}
        return stand_in.fake(method, u, params, headers, body)

    first_read(account3, shop3, failing)
    f = counts(url, shop3)
    print("failed read, notices and entries:", f)
    check(f[0] == 0, "a failed first read leaves no notice")

    print(f"{ok} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
