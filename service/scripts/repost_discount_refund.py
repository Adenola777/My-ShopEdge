"""Posts the discount returned on refund for statements read before 9 October 2026.

    DATABASE_URL=... TIKTOK_APP_KEY=... TIKTOK_APP_SECRET=... TIKTOK_TOKEN_KEY=... \\
        python3 scripts/repost_discount_refund.py STATEMENT_ID [...] [--apply]

Written 9 October 2026 on the owner's ruling that the statements already posted be corrected
(`correct_posting_9_october.sql`). That correction left three statements unreconciled, by 801,
1 and 1 pence. Their fees and shipping match TikTok's header to the penny, and the gap sits
in net sales, which fits `seller_discount_refund_amount`: A11 lists it, the posting never read
it before commit 3c2c475, and it was never stored. So the only way to know is to ask TikTok.

For each named statement it reads TikTok's calculator again for every order settled on it,
and posts only `seller_discount_refund_amount`, exactly as `tiktok_sync._post_order` now
does: a refund line, spread over the order's lines with the same allocation and the same
`source_ref`. It then restates the statement's payout by the amount posted, with source
`system` and a reason, so the statement's entries still come to zero with the payout.

Without `--apply` it writes nothing: every insert runs inside a savepoint that is rolled back,
and it prints what it would post and what each statement's difference would become. A line
already posted is never posted twice, so a second `--apply` adds nothing.

It runs as the daily job does, as `mse_app` inside each account's `tenant()`, and finds the
statements among the shops `shops_due_for_sync()` lists. The ledger is append-only and
nothing here changes or removes an entry.

**Never run against TikTok before 9 October 2026.** Checked locally against the stand-in in
`testdata/tiktok_sync_check.py` only.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg  # noqa: E402

from app import tiktok_sync as ts  # noqa: E402

FIELD = "seller_discount_refund_amount"


def repost(conn, client, shop_id: str, statement: str, apply: bool) -> dict:
    row = conn.execute(
        "select s.id::text, p.occurred_at, p.basis_month, p.settlement_month, p.source_ref "
        "from settlements s join ledger_entries p on p.settlement_id = s.id "
        "and p.category = 'settlement' and p.source = 'tiktok' "
        "where s.shop_id = %s and s.tiktok_statement_id = %s", (shop_id, statement)).fetchone()
    if row is None:
        return {"statement": statement, "error": "not posted for this shop"}
    sid, paid_on, basis_month, smonth, payout_ref = row
    before = conn.execute("select unexplained_minor from settlement_reconciliation "
                          "where settlement_id = %s", (sid,)).fetchone()[0]
    orders = conn.execute(
        "select o.id::text, o.tiktok_order_id from order_settlements os join orders o on o.id = os.order_id "
        "where os.settlement_id = %s order by o.tiktok_order_id", (sid,)).fetchall()
    out = {"statement": statement, "difference_before": int(before), "lines": []}
    with conn.transaction() as tx:
        p = ts._Poster(conn, shop_id, sid, statement, smonth, ts.Tally())
        for order_id, tiktok_order in orders:
            calc = client.call("GET", ts.ORDER_CALC_PATH.format(id=tiktok_order))
            occurred = ts.utc(calc.get("order_create_time")) or conn.execute(
                "select order_created_at from orders where id = %s", (order_id,)).fetchone()[0]
            ret = conn.execute("select id::text from returns where order_id = %s "
                               "order by requested_at desc nulls last limit 1", (order_id,)).fetchone()
            lines_by_sku = ts._order_lines(conn, order_id)
            for index, t in enumerate(calc.get("sku_transactions") or []):
                if t.get("statement_id") not in (None, statement):
                    continue
                amount = ts.pence((t.get("revenue_breakdown") or {}).get(FIELD))
                if not amount:
                    continue
                lines = lines_by_sku.get(t["sku_id"]) or []
                if not lines:
                    raise ts.TikTokError("no_order_line", f"order {tiktok_order} has no line for {t['sku_id']}")
                ref = f"{statement}:{tiktok_order}:{t['sku_id']}:{index}:{FIELD}"
                if conn.execute("select 1 from ledger_entries where shop_id = %s and source_ref = %s",
                                (shop_id, ref)).fetchone():
                    out["lines"].append({"order": tiktok_order, "amount": amount, "already_posted": True})
                    continue
                for line, part in zip(lines, ts.allocate(amount, [1] * len(lines)), strict=True):
                    p.post("refund", part, occurred, ref, order_id=order_id, line=line,
                           allocated=len(lines) > 1, fee_type=FIELD, return_id=ret[0] if ret else None)
                out["lines"].append({"order": tiktok_order, "amount": amount})
        if p.total:
            conn.execute(
                "insert into ledger_entries (shop_id, settlement_id, entry_type, category, amount_minor, "
                "currency, occurred_at, basis_month, settlement_month, source, source_ref, reason, attribution) "
                "values (%s, %s, 'payout', 'settlement', %s, 'GBP', %s, %s, %s, 'system', %s, %s, 'none') "
                "on conflict do nothing",
                (shop_id, sid, -p.total, paid_on, basis_month, smonth,
                 f"{payout_ref}:discount-refund-9-october",
                 "The payout is restated because the discount TikTok returned on a refund had not been counted."))
        after = conn.execute("select unexplained_minor from settlement_reconciliation "
                             "where settlement_id = %s", (sid,)).fetchone()[0]
        balance = conn.execute("select coalesce(sum(amount_minor), 0) from ledger_entries "
                               "where settlement_id = %s and entry_type <> 'reserve'", (sid,)).fetchone()[0]
        out.update(posted=p.total, difference_after=int(after), entries_net=int(balance),
                   applied=apply)
        if int(balance) != 0:
            raise ts.TikTokError("unbalanced", f"statement {statement} would not come to zero")
        if not apply:
            raise psycopg.Rollback(tx)
    return out


def main(argv: list[str]) -> int:
    from app.db import tenant, unscoped
    from app.tiktok_api import client_for, http_transport

    apply = "--apply" in argv
    wanted = [a for a in argv if not a.startswith("--")]
    if not wanted:
        print(__doc__)
        return 2
    with unscoped() as conn:
        due = conn.execute("select shop_id, account_id from shops_due_for_sync()").fetchall()
    results, failed = [], 0
    for shop_id, account_id in due:
        with tenant(account_id) as conn:
            mine = [r[0] for r in conn.execute(
                "select tiktok_statement_id from settlements where shop_id = %s "
                "and tiktok_statement_id = any(%s)", (str(shop_id), wanted)).fetchall()]
            if not mine:
                continue
            client = client_for(conn, shop_id, http_transport)
            for statement in mine:
                try:
                    results.append(repost(conn, client, str(shop_id), statement, apply))
                except Exception as err:  # noqa: BLE001  report it and move on
                    failed += 1
                    results.append({"statement": statement, "error": f"{type(err).__name__}: {err}"})
    found = {r["statement"] for r in results}
    for statement in wanted:
        if statement not in found:
            results.append({"statement": statement, "error": "not found on any shop due for sync"})
            failed += 1
    print(json.dumps(results, indent=2, default=str))
    print(("Applied." if apply else "Dry run, nothing written.") + f" {failed} with an error.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
