"""Runs `listExports` and `listAccountExports` against a local PostgreSQL that carries the schema.

    DATABASE_URL=postgresql://mse_migrator@/mse_check?host=/tmp/pgcheck&port=5499 \\
        python3 testdata/export_list_check.py

Written 8 October 2026, when the two lists were added. The URL must be a role that may set
`mse_app`, as the service's own does. The check makes two accounts of its own, each with a
shop, gives each a spread of jobs, calls the handlers as each account, and removes every row
it made, whether it passes or not. It needs no network and no file store.

What it proves: the newest twenty come first, a ready job past its seven days reads expired
without being written, no list carries a signed link, and neither account sees the other's
jobs, through row level security and through the handlers' own filters.
"""

import sys
import uuid
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "service"))

from app.auth import Account  # noqa: E402
from app.db import pool  # noqa: E402
from app.dates import now_utc  # noqa: E402
from app.exports import list_account_exports, list_exports  # noqa: E402

ok = bad = 0


def check(cond: bool, what: str) -> None:
    global ok, bad
    if cond:
        ok += 1
        print(f"  ok   {what}")
    else:
        bad += 1
        print(f"  FAIL {what}")


def main() -> int:
    tag = uuid.uuid4().hex[:8]
    now = now_utc()
    a, b = uuid.uuid4(), uuid.uuid4()
    shop_a, shop_b = uuid.uuid4(), uuid.uuid4()
    with pool().connection() as conn:
        with conn.transaction():
            for acc, shop in ((a, shop_a), (b, shop_b)):
                conn.execute("insert into accounts (id, email, auth_subject) values (%s, %s, %s)",
                             (str(acc), f"{acc}@check.invalid", f"check-{tag}-{acc}"))
                conn.execute("insert into shops (id, account_id, tiktok_shop_id, connection_status) "
                             "values (%s, %s, %s, 'connected')", (str(shop), str(acc), f"check-{tag}-{shop}"))
            # Account A: 22 shop jobs, the newest ready and fresh, the next ready but past its
            # seven days, one failed, one queued, and eighteen older ready ones.
            for i in range(22):
                status = "failed" if i == 2 else "queued" if i == 3 else "ready"
                created = now - timedelta(hours=i)
                expires = (now - timedelta(minutes=1)) if i == 1 else (created + timedelta(days=7))
                conn.execute(
                    "insert into exports (shop_id, kind, format, basis, period_start, period_end, status, "
                    "created_at, ready_at, expires_at, storage_key, size_bytes, row_count) values "
                    "(%s, 'ledger', 'csv', 'sales', '2026-09-01', '2026-09-30', %s, %s, %s, %s, %s, 10, 1)",
                    (str(shop_a), status, created, created if status == "ready" else None,
                     expires if status == "ready" else None, f"exports/{shop_a}/{i}.csv" if status == "ready" else None),
                )
            conn.execute("insert into exports (shop_id, kind, format, basis, period_start, period_end, status) "
                         "values (%s, 'month_summary', 'xlsx', 'cash', '2026-09-01', '2026-09-30', 'queued')", (str(shop_b),))
            conn.execute("insert into account_exports (account_id, status, requested_at, ready_at, expires_at, storage_key) "
                         "values (%s, 'ready', %s, %s, %s, 'k1')",
                         (str(a), now - timedelta(days=8), now - timedelta(days=8), now - timedelta(days=1)))
            conn.execute("insert into account_exports (account_id, status) values (%s, 'queued')", (str(a),))
            conn.execute("insert into account_exports (account_id, status) values (%s, 'queued')", (str(b),))
    try:
        acc_a = Account(id=a, email="a", name=None, subject="a")
        acc_b = Account(id=b, email="b", name=None, subject="b")

        print("listExports")
        jobs = list_exports(acc_a, shop_a).exports
        check(len(jobs) == 20, f"returns twenty of the twenty two ({len(jobs)})")
        check(all(jobs[i].requested_at >= jobs[i + 1].requested_at for i in range(len(jobs) - 1)), "newest first")
        check([j.status for j in jobs[:4]] == ["ready", "expired", "failed", "queued"],
              f"a ready job past its seven days reads expired ({[j.status for j in jobs[:4]]})")
        check(all(j.download_url is None for j in jobs), "no job carries a signed link")
        check(list_exports(acc_b, shop_a).exports == [], "account B sees nothing of account A's shop")
        check(len(list_exports(acc_b, shop_b).exports) == 1, "account B sees its own one job")
        with pool().connection() as conn:
            stored = conn.execute("select count(*) from exports where shop_id = %s and status = 'expired'",
                                  (str(shop_a),)).fetchone()[0]
        check(stored == 0, "the list wrote nothing")

        print("listAccountExports")
        mine = list_account_exports(acc_a).exports
        check([j.status for j in mine] == ["queued", "expired"], f"newest first, the old one expired ({[j.status for j in mine]})")
        check(all(j.download_url is None for j in mine), "no download carries a signed link")
        check(len(list_account_exports(acc_b).exports) == 1, "account B sees only its own download")
    finally:
        with pool().connection() as conn:
            with conn.transaction():
                for acc, shop in ((a, shop_a), (b, shop_b)):
                    conn.execute("delete from exports where shop_id = %s", (str(shop),))
                    conn.execute("delete from account_exports where account_id = %s", (str(acc),))
                    conn.execute("delete from shops where id = %s", (str(shop),))
                    conn.execute("delete from accounts where id = %s", (str(acc),))
    print(f"\n{ok} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
