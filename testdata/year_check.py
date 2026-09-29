"""Behaviour across twelve months and both clock changes, on the year dataset.

    MSE_TESTDATA_YEAR=1 python3 testdata/generate_payloads.py
    MSE_PAYLOADS=payloads_year MSE_ROWS=rows_year.json python3 testdata/ingest.py
    createdb mse_year
    DATABASE_URL=... python3 service/scripts/migrate.py
    DATABASE_URL=... python3 testdata/load_rows.py testdata/rows_year.json
    DATABASE_URL=... python3 testdata/year_check.py

Written 29 September 2026 for CLAUDE.md fault 8: "Nothing yet tests behaviour across many
months or across the British Summer Time boundary." It needs a database, so it is not in CI.

What it checks:
- The London sale date the database derives for each order placed where UTC and London
  disagree, against the date stated in the generator's comment for that order.
- That the ingester's `basis_month`, worked out in Python, is the month of the database's
  `basis_day` on every entry, so the two sides cannot disagree about a month.
- The settlement month of a statement stamped 23:30 UTC on 31 March, which is April.
- That twelve monthly runs of `money_view.calculate`, the Money screen's arithmetic, sum to
  one run over the whole year, on both bases, for gross sales, net proceeds and kept.

**Run on 29 September 2026** against a database built from empty by `migrate.py`: 20 checks
passed and 2 failed. The two failures are a real finding about the cost rule, not a fault in
this script, and they are recorded in audit/YEAR_dataset_29_september.md. They stay failing
until the owner rules, because a check changed to pass would hide the finding.
"""

import os
import sys
from datetime import date
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "service"))
from app.money_view import calculate  # noqa: E402
from app.trends import _months  # noqa: E402

ok = bad = 0


def order_id(ref):
    """generate_payloads.order_id, copied because importing that script regenerates payloads."""
    import hashlib
    return "5767" + hashlib.sha1(ref.encode()).hexdigest()[:14].upper()


def check(cond, what):
    global ok, bad
    print(("PASS " if cond else "FAIL ") + what)
    ok += bool(cond)
    bad += not cond


# The London date each boundary order must carry, from the generator's comments.
EXPECTED = {
    "YBSTEND1": date(2025, 10, 26), "YBSTEND2": date(2025, 10, 26), "YOCTEND": date(2025, 10, 31),
    "YBSTSTART1": date(2026, 3, 28), "YBSTSTART2": date(2026, 3, 30), "YMAREND": date(2026, 4, 1),
    "A10": date(2026, 8, 1), "A11": date(2026, 7, 31),
}


def main():
    url = os.environ["DATABASE_URL"]

    with psycopg.connect(url) as conn:
        account, shop = conn.execute("select a.id, s.id from accounts a join shops s on s.account_id = a.id").fetchone()
        for ref, want in EXPECTED.items():
            got = conn.execute(
                "select distinct le.basis_day from ledger_entries le join orders o on o.id = le.order_id "
                "where o.tiktok_order_id = %s and le.category = 'gross_sales'", (order_id(ref),)).fetchall()
            check([g[0] for g in got] == [want], f"{ref}: sale dated {got[0][0] if got else None} in London, expected {want}")

        mismatched = conn.execute(
            "select count(*) from ledger_entries where basis_month <> date_trunc('month', basis_day)::date").fetchone()[0]
        total = conn.execute("select count(*) from ledger_entries").fetchone()[0]
        check(mismatched == 0, f"the ingester's month agrees with the database's day on all {total} entries")

        march = conn.execute("select distinct settlement_month from ledger_entries le join settlements s "
                             "on s.id = le.settlement_id where s.tiktok_statement_id = 'Y202603-0001'").fetchall()
        check(march == [(date(2026, 4, 1),)], f"the statement stamped 23:30 UTC on 31 March settles in {march}")

        conn.execute("set role mse_app")
        conn.execute("select set_config('app.account_id', %s, false)", (str(account),))
        months = _months(date(2026, 9, 29))
        span = (months[0][0], months[-1][1])
        for basis in ("sales", "cash"):
            whole = calculate(conn, shop, *span, basis)
            parts = [calculate(conn, shop, s, e, basis) for s, e in months]
            with_sales = sum(1 for p in parts if p.totals.gross_sales.amount_minor)
            for name, get in (("gross sales", lambda v: v.totals.gross_sales.amount_minor),
                              ("net proceeds", lambda v: v.totals.net_proceeds.amount_minor)):
                total_parts = sum(get(p) for p in parts)
                check(total_parts == get(whole),
                      f"{basis} basis {name}: twelve months sum to {total_parts}, the year reads {get(whole)}")
            # Every cost takes effect on 1 July 2026, so a month before July sold units with no
            # cost in force. Kept must be unknown for those months and for the year, never a
            # figure that leaves the goods out (CST-4, the cost in force at the period's end).
            early = [p for (s, _e), p in zip(months, parts, strict=True) if s < date(2026, 7, 1) and p.totals.gross_sales.amount_minor]
            late = [p for (s, _e), p in zip(months, parts, strict=True) if s >= date(2026, 7, 1)]
            check(all(p.kept is None and p.kept_reason == "incomplete_costs" for p in early),
                  f"{basis} basis: kept is unknown in the {len(early)} months with sales before any cost took effect")
            check(all(p.kept is not None or p.kept_reason == "no_sales" for p in late),
                  f"{basis} basis: kept is known from July, when the costs took effect")
            check(whole.kept is None and whole.kept_reason == "incomplete_costs",
                  f"{basis} basis: the year's kept is unknown too, rather than a figure that leaves goods out")
            check(with_sales >= 10, f"{basis} basis: {with_sales} of twelve months hold sales")

    print(f"{ok} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
