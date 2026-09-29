"""Gives one account a demo shop filled with the year dataset. For the demo service only.

    cd service
    DATABASE_URL=... DEMO_ACCOUNT_SUBJECT=... DEMO_ACCOUNT_EMAIL=... \
        python3 ../testdata/load_demo.py

Written 29 September 2026, when the owner chose to reach the dashboard through a demo shop
on the development branch while TikTok's review blocks a real connection (A24). The demo
Render service runs it once before it starts. It must never be run against production:
every figure it writes is made up.

It works entirely as the service does, as `mse_app` inside `tenant()`, so row level security
holds and it needs no role beyond the service's own. The account comes from
`create_account`, the subscription from `create_subscription` and
`apply_subscription_event`, and every other row is an ordinary insert scoped to the account.

What it changes from `rows_year.json`, and why:

  * Every id is replaced, derived from the account, so the demo shop cannot collide with the
    synthetic shop already on the branch, which the generator gave the same ids.
  * The shop is named "Demo shop (sample data)" and its TikTok id is `DEMO-` and the account,
    so nobody mistakes it for a connected shop.
  * Costs take effect on 1 January 2025 instead of 1 July 2026. Under A31.4 a unit is costed
    on its sale date, and the year dataset starts in October 2025, so with July's date nine
    of the twelve months would read kept as unknown. The demo is for walking the screens.
  * The subscription is a Growth trial whose customer id begins `demo_`, which Stripe never
    issues, so the billing screens show a trial and nothing reaches Stripe.

It does nothing when the account already owns a shop, so a restart adds nothing.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "service"))

from psycopg.types.json import Jsonb  # noqa: E402

from app.db import tenant, unscoped  # noqa: E402

ROWS = HERE / os.environ.get("MSE_ROWS", "rows_year.json")
NAMESPACE = uuid.UUID("5f1c6f0e-6d0a-4c47-9a53-0d1b3f5a2e71")
PLACEHOLDER = b"\x00"
COSTS_FROM = "2025-01-01"
ORDER = ("shops", "tiktok_connections", "products", "skus", "orders", "order_lines",
         "settlements", "order_settlements", "returns", "return_items", "ledger_entries",
         "stock_positions", "stock_movements", "product_costs", "discrepancies")


def is_uuid(value) -> bool:
    if not isinstance(value, str) or len(value) != 36:
        return False
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def main() -> int:
    subject = os.environ["DEMO_ACCOUNT_SUBJECT"]
    email = os.environ["DEMO_ACCOUNT_EMAIL"]
    name = os.environ.get("DEMO_ACCOUNT_NAME") or email

    with unscoped() as conn:
        account = conn.execute("select create_account(%s, %s, %s)", (subject, email, name)).fetchone()[0]
    with tenant(account) as conn:
        has_shop = conn.execute("select count(*) from shops").fetchone()[0] > 0
        has_plan = conn.execute("select count(*) from subscriptions").fetchone()[0] > 0
    counts = load_shop(account) if not has_shop else "account already owns a shop"
    plan = start_trial(account) if not has_plan else "account already has a subscription"
    print(json.dumps({"account": str(account), "shop": counts, "subscription": plan}))
    return 0


def load_shop(account) -> dict:
    rows = json.load(open(ROWS))
    old_account = rows["accounts"][0]["id"]

    def remap(value):
        if value == old_account:
            return str(account)
        if is_uuid(value):
            return str(uuid.uuid5(NAMESPACE, f"{account}:{value}"))
        return value

    counts = {}
    with tenant(account) as conn:
        for table in ORDER:
            for item in rows.get(table) or []:
                item = {k: remap(v) for k, v in item.items()}
                if table == "shops":
                    item.update(tiktok_shop_id=f"DEMO-{account}", shop_name="Demo shop (sample data)",
                                seller_type="LOCAL", connection_status="connected")
                if table == "tiktok_connections":
                    item.setdefault("access_token_enc", PLACEHOLDER)
                    item.setdefault("refresh_token_enc", PLACEHOLDER)
                if table == "product_costs":
                    item["effective_from"] = COSTS_FROM
                cols = list(item)
                vals = [Jsonb(v) if isinstance(v, dict) else v for v in item.values()]
                conn.execute(f"insert into {table} ({', '.join(cols)}) "
                             f"values ({', '.join(['%s'] * len(cols))})", vals)
            counts[table] = len(rows.get(table) or [])
        conn.execute("update shops set first_synced_at = now(), last_synced_at = now()")
    return counts


def start_trial(account) -> str:
    customer = f"demo_{account}"
    now = datetime.now(timezone.utc)
    with unscoped() as conn:
        conn.execute("select create_subscription(%s, 'growth', %s)", (str(account), customer))
        conn.execute("select apply_subscription_event(%s, null, 'growth', 'trialing', %s, %s, %s, false)",
                     (customer, now + timedelta(days=30), now, now + timedelta(days=30)))
    return "growth trial, customer " + customer


if __name__ == "__main__":
    raise SystemExit(main())
