"""Checks the fields the posting was corrected for on 9 October 2026.

    createdb mse_posting
    DATABASE_URL=... python3 service/scripts/migrate.py
    DATABASE_URL=... python3 testdata/posting_fields_check.py

It needs a database built from empty by `migrate.py`, and it answers every TikTok request
through the stand-in in `tiktok_sync_check.py`, so nothing reaches TikTok. The ledger is
append-only, so the database is dropped afterwards.

The generated payloads carry none of these fields, so this script adds them to statement
202608A-0001 the way production showed them (tiktok_sync's docstring, FIELDS CORRECTED):

- `affiliate_commission_amount_before_pit` as a copy of `affiliate_commission_amount`, and
  `tiktok_shop_shipping_incentive_amount` as a copy of `shipping_fee_discount_amount`. Neither
  changes the statement's total, because each repeats a field already counted.
- `seller_discount_refund_amount` of 1.00, `smart_promotion_fee_amount` of -0.25 and
  `free_return_subsidy_amount` of 0.35, each added to the statement's total as well.

It checks that every statement reconciles to the penny, that the two repeated fields are not
posted, and that the three others land in their categories.

**Run on 9 October 2026** against a database built from empty by `migrate.py`: every check
passed with the change, and the reconciliation check failed without it.
"""

import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tiktok_sync_check as stand_in  # noqa: E402  sets the TikTok variables and the path

import psycopg  # noqa: E402

from app import tiktok_sync  # noqa: E402
from app.connections import _encrypt  # noqa: E402

STATEMENT = "202608A-0001"
NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
ok = bad = 0


def check(cond, what):
    global ok, bad
    print(("PASS " if cond else "FAIL ") + what)
    ok += bool(cond)
    bad += not cond


def add_fields():
    """Adds the five fields to the statement's orders, and its total moves by what they bring."""
    orders = [t["order_id"] for t in stand_in.STMT_TXNS[STATEMENT]["data"]["transactions"]
              if t.get("type") == "ORDER"]
    skus = [t for o in orders for t in stand_in.ORDER_CALC[o]["data"]["sku_transactions"]]
    copied = 0
    for t in skus:
        fee = t["fee_tax_breakdown"]["fee"]
        if fee.get("affiliate_commission_amount") not in (None, "", "0", "0.00"):
            fee["affiliate_commission_amount_before_pit"] = fee["affiliate_commission_amount"]
            copied += 1
    first = skus[0]
    first["shipping_cost_breakdown"]["shipping_fee_discount_amount"] = "0.40"
    first["shipping_cost_breakdown"]["tiktok_shop_shipping_incentive_amount"] = "0.40"
    first["revenue_breakdown"]["seller_discount_refund_amount"] = "1.00"
    first["fee_tax_breakdown"]["fee"]["smart_promotion_fee_amount"] = "-0.25"
    first["shipping_cost_breakdown"]["free_return_subsidy_amount"] = "0.35"
    moved = Decimal("0.40") + Decimal("1.00") - Decimal("0.25") + Decimal("0.35")
    for s in stand_in.STATEMENTS:
        if s["id"] == STATEMENT:
            s["settlement_amount"] = str(Decimal(s["settlement_amount"]) + moved)
    return copied


def main():
    url = os.environ["DATABASE_URL"]
    copied = add_fields()
    check(copied > 0, f"the statement carries an affiliate commission to copy ({copied})")
    with psycopg.connect(url) as conn:
        account = conn.execute(
            "insert into accounts (email, auth_subject, display_name) values "
            "('posting@example.test', 'stack|posting', 'Posting') returning id").fetchone()[0]
        shop = conn.execute(
            "insert into shops (account_id, tiktok_shop_id, shop_name, region, seller_type, currency, "
            "connection_status) values (%s, 'posting', 'Posting shop', 'GB', 'LOCAL', 'GBP', 'pending') "
            "returning id", (account,)).fetchone()[0]
        conn.execute(
            "insert into tiktok_connections (shop_id, access_token_enc, refresh_token_enc, shop_cipher_enc, "
            "access_expires_at, refresh_expires_at, scopes) values (%s, %s, %s, %s, now() + interval '6 days', "
            "now() + interval '300 days', '{seller.finance.info,seller.order.info}')",
            (shop, _encrypt("access"), _encrypt("refresh"), _encrypt("cipher-x")))
    result = tiktok_sync.run_one(shop, account, stand_in.fake, NOW)
    print("read:", result.get("sync"))
    with psycopg.connect(url) as conn:
        rec = conn.execute(
            "select tiktok_statement_id, unexplained_minor from settlement_reconciliation "
            "where shop_id = %s order by 1", (shop,)).fetchall()
        types = dict(conn.execute(
            "select tiktok_fee_type, string_agg(distinct category, ',') from ledger_entries "
            "where shop_id = %s and tiktok_fee_type is not null group by 1", (shop,)).fetchall())
    print("reconciliation:", rec)
    check(len(rec) == 3 and all(int(u) == 0 for _, u in rec), "every statement reconciles to the penny")
    check("affiliate_commission_amount_before_pit" not in types,
          "the commission before personal income tax is not posted")
    check("tiktok_shop_shipping_incentive_amount" not in types, "the shipping incentive is not posted")
    check(types.get("shipping_fee_discount_amount") == "shipping_fee", "the shipping discount is posted once")
    check(types.get("seller_discount_refund_amount") == "refund", "the discount returned on refund is a refund line")
    check(types.get("smart_promotion_fee_amount") == "smart_promotions_fee", "the smart promotion fee has its category")
    check(types.get("free_return_subsidy_amount") == "return_shipping", "the free return subsidy is return shipping")
    print(f"{ok} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
