"""Checks `service/scripts/repost_discount_refund.py` before it reaches TikTok. 9 October 2026.

    createdb mse_repost
    DATABASE_URL=... python3 service/scripts/migrate.py
    DATABASE_URL=... python3 testdata/repost_discount_refund_check.py

It needs a database built from empty by `migrate.py`, and answers every TikTok request through
the stand-in in `tiktok_sync_check.py`. It reproduces what production holds: statement
202608A-0001 is posted while TikTok's calculator carries no `seller_discount_refund_amount`,
and its total is one pound more than its entries, so it does not reconcile. TikTok's answer
then carries the field at 1.00, as the three real statements are believed to, and the script
is run against it.

It checks that a dry run writes nothing, that `--apply` posts one refund line and restates the
payout so the statement reconciles and still comes to zero, and that a second run adds nothing.

**Run on 9 October 2026** against a database built from empty by `migrate.py`: every check passed.
"""

import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "service" / "scripts"))

import tiktok_sync_check as stand_in  # noqa: E402  sets the TikTok variables and the path

import psycopg  # noqa: E402
import repost_discount_refund as repost  # noqa: E402

from app import tiktok_sync  # noqa: E402
from app.connections import _encrypt  # noqa: E402
from app.db import tenant  # noqa: E402
from app.tiktok_api import client_for  # noqa: E402

STATEMENT = "202608A-0001"
NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
ok = bad = 0


def check(cond, what):
    global ok, bad
    print(("PASS " if cond else "FAIL ") + what)
    ok += bool(cond)
    bad += not cond


def state(url, shop):
    with psycopg.connect(url) as conn:
        return conn.execute(
            "select r.unexplained_minor, (select count(*) from ledger_entries where shop_id = %(s)s), "
            "(select coalesce(sum(amount_minor), 0) from ledger_entries le where le.settlement_id = r.settlement_id "
            " and entry_type <> 'reserve') from settlement_reconciliation r "
            "where r.shop_id = %(s)s and r.tiktok_statement_id = %(t)s", {"s": shop, "t": STATEMENT}).fetchone()


def main():
    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url) as conn:
        account = conn.execute(
            "insert into accounts (email, auth_subject, display_name) values "
            "('repost@example.test', 'stack|repost', 'Repost') returning id").fetchone()[0]
        shop = str(conn.execute(
            "insert into shops (account_id, tiktok_shop_id, shop_name, region, seller_type, currency, "
            "connection_status) values (%s, 'repost', 'Repost shop', 'GB', 'LOCAL', 'GBP', 'pending') "
            "returning id", (account,)).fetchone()[0])
        conn.execute(
            "insert into tiktok_connections (shop_id, access_token_enc, refresh_token_enc, shop_cipher_enc, "
            "access_expires_at, refresh_expires_at, scopes) values (%s, %s, %s, %s, now() + interval '6 days', "
            "now() + interval '300 days', '{seller.finance.info,seller.order.info}')",
            (shop, _encrypt("access"), _encrypt("refresh"), _encrypt("cipher-x")))

    # As production was read: TikTok's total includes a discount returned on refund that the
    # calculator did not yet carry, so the statement is one pound out.
    for s in stand_in.STATEMENTS:
        if s["id"] == STATEMENT:
            s["settlement_amount"] = str(Decimal(s["settlement_amount"]) + 1)
    tiktok_sync.run_one(shop, account, stand_in.fake, NOW)
    before = state(url, shop)
    print("before:", before)
    check(int(before[0]) == 100 and int(before[2]) == 0, "the statement is 100 pence out and still comes to zero")

    first = next(t["order_id"] for t in stand_in.STMT_TXNS[STATEMENT]["data"]["transactions"]
                 if t.get("type") == "ORDER")
    stand_in.ORDER_CALC[first]["data"]["sku_transactions"][0]["revenue_breakdown"][repost.FIELD] = "1.00"

    with tenant(account) as conn:
        client = client_for(conn, shop, stand_in.fake)
        dry = repost.repost(conn, client, shop, STATEMENT, apply=False)
    print("dry:", dry)
    check(dry.get("posted") == 100 and dry.get("difference_after") == 0 and state(url, shop) == before,
          "a dry run finds 100 pence, says it would reconcile, and writes nothing")

    with tenant(account) as conn:
        client = client_for(conn, shop, stand_in.fake)
        done = repost.repost(conn, client, shop, STATEMENT, apply=True)
    after = state(url, shop)
    print("applied:", done, after)
    check(int(after[0]) == 0 and int(after[2]) == 0, "applied, the statement reconciles and still comes to zero")
    check(after[1] == before[1] + 2, "one refund line and one payout line were added")
    with psycopg.connect(url) as conn:
        kinds = conn.execute(
            "select category, source, amount_minor from ledger_entries where shop_id = %s and "
            "(tiktok_fee_type = %s or source_ref like '%%discount-refund-9-october') order by category",
            (shop, repost.FIELD)).fetchall()
    print("added:", kinds)
    check(kinds == [("refund", "tiktok", 100), ("settlement", "system", -100)],
          "the refund line is TikTok's and the payout restatement is the system's")

    with tenant(account) as conn:
        client = client_for(conn, shop, stand_in.fake)
        again = repost.repost(conn, client, shop, STATEMENT, apply=True)
    check(state(url, shop) == after and again.get("posted") == 0, "a second run adds nothing")

    print(f"{ok} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
