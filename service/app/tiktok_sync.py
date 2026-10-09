"""Reading orders, returns and statements from TikTok into MyShopEdge. Part 1 of the batch.

**Unverified against a live call.** It has run only against the generated payloads in
`testdata/payloads`, through a transport that answers from those files
(`testdata/tiktok_sync_check.py`). The request shapes it relies on without a recorded fact
are named in `tiktok_api.UNVERIFIED`, and the response fields it relies on without a recorded
real payload are listed under UNVERIFIED FIELDS below.

THE LEDGER RULE, RULED 29 SEPTEMBER 2026

The ledger is append-only, and TikTok states an order's final money only when it settles.
The owner ruled that order money enters the ledger once, at settlement, already carrying its
statement and the month it settled. Nothing is ever reversed. So:

  * `sync_orders` writes orders, products, variants and order lines. No ledger entry.
  * `sync_returns` writes returns and their items. No ledger entry. It runs before the
    finance sync, so a refund settled later can carry its return.
  * `sync_finance` reads each statement once. For every order it pays, the per-order
    calculator gives the SKU breakdown (A11.2), and every entry is posted with the statement
    and its London month. A statement already posted is never posted again; only its payment
    status and payment time are brought up to date, because `settlements` is not append-only.

A consequence the owner accepted: a sale shows on the sales basis only once it settles, so
recent weeks read low and the screens mark them incomplete.

THE MAPPING

Every mapping rule is the one `testdata/ingest.py` applies, because the screens were built
and checked against that ingester's output (A11.2, A11.3, A17.1, A19.5). Five differences:

  * No `cost_of_goods_sold` entry. Every figure reads cost from `product_costs` on each
    unit's sale date (A31.4), and the product and money queries already exclude the category.
  * The payout is posted as the negative of what this statement's own entries came to.
    `ingest.py` summed every entry of each order, which is the same thing only when an order
    settles on one statement.
  * `source_ref` names the statement and TikTok's own field, so two fee fields sharing a
    category on one line, or one order settling across two statements, cannot collide on the
    ledger's idempotency index. The ingester's references could.
  * A stock write-off is not posted here. It follows the seller's own check of a returned
    item (checkReturnItem, A30.2), not anything TikTok states.
  * The fields corrected on 9 October 2026, below. The ingester was left as it was, because
    the generated payloads carry none of them and changing it would rebuild `rows.json`.
    `testdata/posting_fields_check.py` covers them instead.

FIELDS CORRECTED ON 9 OCTOBER 2026, FROM PRODUCTION

Production then held 107 real statements, and 78 did not reconcile: the statement's own
total differed from what its entries came to. Querying the ledger found why.

  * Two fields repeat another field and are not posted (RESTATED). On every row on
    production, `affiliate_commission_amount_before_pit` equalled `affiliate_commission_amount`
    (216 of 216) and `tiktok_shop_shipping_incentive_amount` equalled
    `shipping_fee_discount_amount` (36 of 36). Each statement's own fee and shipping totals
    match only when they are left out. Posting both counted the commission twice.
    Leaving the two out reconciled 104 of the 107 statements.
  * `seller_discount_refund_amount`, which A11 lists as "Discounts returned on refund", was
    never posted. It is posted now, as a refund line, so a refund reads as what the customer
    got back. **Unverified**: the field is not stored, so its effect is inferred. On statement
    7686421137164715798 the fees and shipping match TikTok's header to the penny and net sales
    are short by exactly 801, the size of a discount on the refunded item. The other two
    statements still out are short by 1 pence each. The first statement read after this
    change that carries the field will settle it.
  * `smart_promotion_fee_amount` and `free_return_subsidy_amount` were posted as
    `unmapped_fee`. Their money was right, and they now carry their own categories, the
    second as A11 lists it under return shipping.

UNVERIFIED FIELDS

  * `line_items[].quantity` is not read: each line item is taken as one unit, as the
    ingester does. No real order payload is in the repository to settle it.
  * `return_line_items[].sku_id` for the items of a return. The generated payload carries a
    private `_skus` list instead, which `testdata/tiktok_sync_check.py` translates.
  * `sku_transactions[].statement_id` on the per-order calculator. Where it is absent every
    SKU transaction is taken to belong to the statement being read.
  * `return_status` value `RETURN_OR_REFUND_REQUEST_COMPLETE` as the mark of a completed
    refund, taken from the generated payload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from psycopg.types.json import Jsonb

from .tiktok_api import (
    INVENTORY_MAX_PRODUCTS,
    INVENTORY_SEARCH_PATH,
    ORDER_CALC_PATH,
    ORDER_DETAIL_IDS_PARAM,
    ORDER_DETAIL_MAX_IDS,
    ORDER_DETAIL_PATH,
    ORDER_SEARCH_BODY,
    ORDER_SEARCH_PATH,
    RETURN_SEARCH_BODY,
    RETURN_SEARCH_PATH,
    STATEMENT_TXNS_PATH,
    STATEMENTS_PATH,
    Client,
    TikTokError,
)

LONDON = ZoneInfo("Europe/London")

# The ingester's maps, unchanged. testdata/ingest.py records where each came from.
FEE_MAP = {
    "platform_commission_amount": "platform_commission",
    "affiliate_commission_amount": "affiliate_commission",
    "affiliate_ads_commission_amount": "affiliate_commission",
    "affiliate_partner_commission_amount": "affiliate_commission",
    "transaction_fee_amount": "transaction_fee",
    "refund_administration_fee_amount": "return_handling_fee",
    "cofunded_promotion_service_fee_amount": "smart_promotions_fee",
    "smart_promotion_fee_amount": "smart_promotions_fee",
}
SHIP_MAP = {
    "actual_shipping_fee_amount": "shipping_fee",
    "customer_paid_shipping_fee_amount": "shipping_fee",
    "shipping_fee_discount_amount": "shipping_fee",
    "fbt_free_shipping_fee_amount": "fbt_shipping_fee",
    "return_shipping_fee_amount": "return_shipping",
    "free_return_subsidy_amount": "return_shipping",
}
# Fields that repeat another field on the same transaction, so posting them counts the money
# twice. Proved on production on 9 October 2026; see FIELDS CORRECTED in the docstring.
RESTATED = {"affiliate_commission_amount_before_pit", "tiktok_shop_shipping_incentive_amount"}
# UK VAT is not a MyShopEdge deduction category. Every other tax field is recorded when it
# carries money, and the run is then partial, because money would otherwise leave the
# ledger with nothing to find it by (A19.5).
TAX_MAP: dict[str, str | None] = {"local_vat_amount": None}
ENTRY_TYPE = {
    "gross_sales": "sale", "seller_discount": "sale", "refund": "refund",
    "platform_commission": "platform_deduction", "affiliate_commission": "platform_deduction",
    "transaction_fee": "platform_deduction", "smart_promotions_fee": "platform_deduction",
    "shipping_fee": "platform_deduction", "return_handling_fee": "platform_deduction",
    "fbt_shipping_fee": "platform_deduction", "unmapped_fee": "platform_deduction",
    "return_shipping": "return_cost", "platform_adjustment": "adjustment",
    "reserve_withheld": "reserve", "reserve_released": "reserve", "settlement": "payout",
}
RETURN_CATEGORIES = {"refund", "return_shipping", "return_handling_fee"}
RETURN_KINDS = {"CANCELLATION": "cancellation", "REFUND_ONLY": "refund_only",
                "RETURN_REFUND": "return_refund"}
REFUND_COMPLETE = "RETURN_OR_REFUND_REQUEST_COMPLETE"   # UNVERIFIED, see the docstring

MINOR_UNIT_EXPONENT = {"GBP": 2}   # testdata/ingest.py, A20.3


def pence(value: Any, currency: str = "GBP") -> int:
    """Decimal, never float (A13 rule 3). An unverified currency raises (A20.3)."""
    if currency not in MINOR_UNIT_EXPONENT:
        raise ValueError(f"No verified minor unit for {currency}.")
    if value in (None, ""):
        return 0
    scale = Decimal(10) ** MINOR_UNIT_EXPONENT[currency]
    return int((Decimal(str(value)) * scale).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def allocate(total: int, weights: list[int]) -> list[int]:
    """Largest remainder, as the ingester and migration 0004 require. No residual pence."""
    if not weights or sum(weights) == 0:
        return [total] + [0] * (len(weights) - 1)
    tw = sum(weights)
    base = [total * w // tw for w in weights]
    rem = total - sum(base)
    order = sorted(range(len(weights)), key=lambda i: -((total * weights[i]) % tw))
    step = 1 if rem > 0 else -1
    for k in range(abs(rem)):
        base[order[k % len(order)]] += step
    return base


def utc(epoch: int | None) -> datetime | None:
    return datetime.fromtimestamp(int(epoch), timezone.utc) if epoch else None


def london_month(when: datetime):
    return when.astimezone(LONDON).date().replace(day=1)


@dataclass
class Tally:
    read: int = 0
    written: int = 0
    failed: int = 0
    notes: list[str] = field(default_factory=list)


# --- orders ----------------------------------------------------------------------------------

def upsert_order(conn, shop_id: str, o: dict[str, Any]) -> str:
    """One order, its products, variants and lines. Returns the order's id.

    SYN-7: `buyer_email` and `recipient_address` are never read, so they are never stored.
    """
    currency = (o.get("payment") or {}).get("currency") or "GBP"
    for line in o.get("line_items") or []:
        product = conn.execute(
            "insert into products (shop_id, tiktok_product_id, title) values (%s, %s, %s) "
            "on conflict (shop_id, tiktok_product_id) do update set title = excluded.title, "
            "updated_at = now() returning id",
            (shop_id, line["product_id"], line.get("product_name"))).fetchone()[0]
        conn.execute(
            "insert into skus (shop_id, product_id, tiktok_sku_id, seller_sku, variant_label) "
            "values (%s, %s, %s, %s, %s) on conflict (shop_id, tiktok_sku_id) do update set "
            "seller_sku = excluded.seller_sku, variant_label = excluded.variant_label, "
            "updated_at = now()",
            (shop_id, product, line["sku_id"], line.get("seller_sku") or None, line.get("sku_name")))
    order_id = conn.execute(
        "insert into orders (shop_id, tiktok_order_id, status, order_created_at, currency, "
        "gross_minor, sales_channel, last_event_at) values (%s, %s, %s, %s, %s, %s, "
        "'tiktok_shop', %s) on conflict (shop_id, tiktok_order_id) do update set "
        "status = excluded.status, last_event_at = excluded.last_event_at returning id",
        (shop_id, o["id"], o.get("status") or "UNKNOWN", utc(o["create_time"]), currency,
         pence((o.get("payment") or {}).get("original_total_product_price"), currency),
         utc(o.get("update_time")))).fetchone()[0]
    for line in o.get("line_items") or []:
        conn.execute(
            "insert into order_lines (shop_id, order_id, sku_id, tiktok_line_id, quantity, "
            "unit_price_minor, seller_discount_minor) "
            "select %s, %s, k.id, %s, 1, %s, 0 from skus k where k.shop_id = %s and k.tiktok_sku_id = %s "
            "on conflict (order_id, tiktok_line_id) do nothing",
            (shop_id, str(order_id), line["id"], pence(line.get("sale_price"), currency),
             shop_id, line["sku_id"]))
    return str(order_id)


def ensure_orders(conn, shop_id: str, client: Client, tiktok_ids: list[str]) -> dict[str, str]:
    """The MyShopEdge id of each TikTok order, fetching any not yet held."""
    known = dict(conn.execute(
        "select tiktok_order_id, id::text from orders where shop_id = %s and tiktok_order_id = any(%s)",
        (shop_id, tiktok_ids)).fetchall())
    missing = [t for t in tiktok_ids if t not in known]
    for i in range(0, len(missing), ORDER_DETAIL_MAX_IDS):
        batch = missing[i:i + ORDER_DETAIL_MAX_IDS]
        data = client.call("GET", ORDER_DETAIL_PATH, {ORDER_DETAIL_IDS_PARAM: ",".join(batch)})
        for o in data.get("orders") or []:
            known[o["id"]] = upsert_order(conn, shop_id, o)
    return known


def sync_orders(conn, shop_id: str, client: Client, since: datetime, until: datetime) -> Tally:
    tally = Tally()
    body = {ORDER_SEARCH_BODY[0]: int(since.timestamp()), ORDER_SEARCH_BODY[1]: int(until.timestamp())}
    for page in client.pages("POST", ORDER_SEARCH_PATH,
                             {"sort_field": "update_time", "sort_order": "ASC"}, body):
        for o in page.get("orders") or []:
            tally.read += 1
            with conn.transaction():
                upsert_order(conn, shop_id, o)
            tally.written += 1
    return tally


# --- returns ---------------------------------------------------------------------------------

def return_skus(r: dict[str, Any]) -> list[str]:
    """UNVERIFIED: `return_line_items[].sku_id`, one unit per item. See the docstring."""
    return [item["sku_id"] for item in r.get("return_line_items") or [] if item.get("sku_id")]


def sync_returns(conn, shop_id: str, client: Client, since: datetime, until: datetime) -> Tally:
    tally = Tally()
    body = {RETURN_SEARCH_BODY[0]: int(since.timestamp()), RETURN_SEARCH_BODY[1]: int(until.timestamp())}
    for page in client.pages("POST", RETURN_SEARCH_PATH,
                             {"sort_field": "update_time", "sort_order": "ASC"}, body):
        for r in page.get("return_orders") or []:
            tally.read += 1
            kind = RETURN_KINDS.get(r.get("return_type") or "")
            if kind is None:
                tally.failed += 1
                tally.notes.append(f"return {r.get('return_id')}: unknown return_type {r.get('return_type')!r}")
                continue
            with conn.transaction():
                order_id = ensure_orders(conn, shop_id, client, [r["order_id"]]).get(r["order_id"])
                if order_id is None:
                    tally.failed += 1
                    tally.notes.append(f"return {r['return_id']}: TikTok returned no order {r['order_id']}")
                    continue
                refund = r.get("refund_amount") or {}
                completed = utc(r.get("update_time")) if r.get("return_status") == REFUND_COMPLETE else None
                row = conn.execute(
                    "insert into returns (shop_id, order_id, tiktok_return_id, kind, status, "
                    "requested_at, refund_completed_at, refund_minor, reason_code, "
                    "tiktok_credit_note_number) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "on conflict (shop_id, tiktok_return_id) do update set status = excluded.status, "
                    "refund_completed_at = coalesce(returns.refund_completed_at, excluded.refund_completed_at), "
                    "refund_minor = excluded.refund_minor, "
                    "tiktok_credit_note_number = coalesce(excluded.tiktok_credit_note_number, "
                    "  returns.tiktok_credit_note_number) "
                    "returning id, (xmax = 0) as inserted",
                    (shop_id, order_id, r["return_id"], kind, r.get("return_status") or "UNKNOWN",
                     utc(r.get("create_time")), completed,
                     -pence(refund.get("refund_total"), refund.get("currency") or "GBP"),
                     r.get("return_reason_text"), r.get("credit_note_number"))).fetchone()
                if row[1]:
                    # Items are written once, with the return. A cancellation or a refund with
                    # no goods back needs no check; goods coming back wait for the seller's
                    # (REC-2, A30.2).
                    check = "not_applicable" if kind in ("cancellation", "refund_only") else "pending"
                    for sku in return_skus(r):
                        conn.execute(
                            "insert into return_items (shop_id, return_id, sku_id, quantity, "
                            "seller_check_status) select %s, %s, k.id, 1, %s from skus k "
                            "where k.shop_id = %s and k.tiktok_sku_id = %s",
                            (shop_id, str(row[0]), check, shop_id, sku))
            tally.written += 1
    return tally


# --- statements ------------------------------------------------------------------------------

class _Poster:
    """Collects one statement's entries, so the payout can be the negative of their sum."""

    def __init__(self, conn, shop_id: str, settlement_id: str, statement_id: str,
                 settlement_month, tally: Tally):
        self.conn, self.shop, self.sid, self.stmt = conn, shop_id, settlement_id, statement_id
        self.smonth, self.tally, self.total = settlement_month, tally, 0

    def post(self, category: str, amount: int, occurred: datetime, ref: str, *,
             order_id: str | None = None, line: tuple[str, str] | None = None,
             allocated: bool = False, fee_type: str | None = None, return_id: str | None = None,
             counted: bool = True) -> None:
        if amount == 0 and category != "settlement":
            return
        attribution = ("allocated" if allocated else "direct") if line else "none"
        row = self.conn.execute(
            "insert into ledger_entries (shop_id, order_id, return_id, settlement_id, entry_type, "
            "category, amount_minor, currency, occurred_at, basis_month, settlement_month, source, "
            "source_ref, tiktok_fee_type, order_line_id, sku_id, attribution) values "
            "(%s, %s, %s, %s, %s, %s, %s, 'GBP', %s, %s, %s, 'tiktok', %s, %s, %s, %s, %s) "
            "on conflict do nothing returning id",
            (self.shop, order_id, return_id, self.sid, ENTRY_TYPE[category], category, amount,
             occurred, london_month(occurred), self.smonth, ref, fee_type,
             line[0] if line else None, line[1] if line else None, attribution)).fetchone()
        if row is None:
            # A statement is posted once, inside one savepoint, so nothing it writes can
            # already exist. A conflict means two of its own entries share a key, and letting
            # one vanish would drop money while the payout still counted it.
            raise TikTokError("ledger_collision", f"statement {self.stmt}: two entries share {ref}")
        if counted:
            self.total += amount
        self.tally.written += 1


def _order_lines(conn, order_id: str) -> dict[str, list[tuple[str, str]]]:
    """The order's lines per TikTok SKU, in a fixed order so allocation is repeatable."""
    out: dict[str, list[tuple[str, str]]] = {}
    for tiktok_sku, line_id, sku_id in conn.execute(
            "select k.tiktok_sku_id, ol.id::text, k.id::text from order_lines ol "
            "join skus k on k.id = ol.sku_id where ol.order_id = %s order by ol.tiktok_line_id",
            (order_id,)).fetchall():
        out.setdefault(tiktok_sku, []).append((line_id, sku_id))
    return out


def _post_order(p: _Poster, conn, order_id: str, tiktok_order: str, calc: dict[str, Any]) -> None:
    lines_by_sku = _order_lines(conn, order_id)
    occurred = utc(calc.get("order_create_time"))
    if occurred is None:
        occurred = conn.execute("select order_created_at from orders where id = %s", (order_id,)).fetchone()[0]
    ret = conn.execute(
        "select id::text from returns where order_id = %s order by requested_at desc nulls last limit 1",
        (order_id,)).fetchone()
    return_id = ret[0] if ret else None
    for index, t in enumerate(calc.get("sku_transactions") or []):
        if t.get("statement_id") not in (None, p.stmt):
            continue
        lines = lines_by_sku.get(t["sku_id"])
        if not lines:
            raise TikTokError("no_order_line", f"order {tiktok_order} has no line for SKU {t['sku_id']}")
        weights = [1] * len(lines)
        # The position in TikTok's list keeps two transactions for one SKU apart.
        stem = f"{p.stmt}:{tiktok_order}:{t['sku_id']}:{index}"

        def spread(category: str, total: int, fee_type: str, stem=stem, lines=lines, weights=weights) -> None:
            rid = return_id if category in RETURN_CATEGORIES else None
            for line, amount in zip(lines, allocate(total, weights), strict=True):
                p.post(category, amount, occurred, f"{stem}:{fee_type}",
                       order_id=order_id, line=line, allocated=len(lines) > 1, fee_type=fee_type,
                       return_id=rid)

        rb = t.get("revenue_breakdown") or {}
        spread("gross_sales", pence(rb.get("subtotal_before_discount_amount")), "subtotal_before_discount_amount")
        spread("seller_discount", pence(rb.get("seller_discount_amount")), "seller_discount_amount")
        spread("refund", pence(rb.get("refund_subtotal_before_discount_amount")),
               "refund_subtotal_before_discount_amount")
        spread("refund", pence(rb.get("seller_discount_refund_amount")), "seller_discount_refund_amount")
        breakdown = t.get("fee_tax_breakdown") or {}
        for fee, amount in (breakdown.get("fee") or {}).items():
            if fee in RESTATED:
                continue
            spread(FEE_MAP.get(fee, "unmapped_fee"), pence(amount), fee)
        for tax, amount in (breakdown.get("tax") or {}).items():
            if tax not in TAX_MAP and pence(amount):
                p.tally.notes.append(f"statement {p.stmt}: tax field {tax} carried {amount} and is not mapped")
                p.tally.failed += 1
        for ship, amount in (t.get("shipping_cost_breakdown") or {}).items():
            if ship == "supplementary_component" or ship in RESTATED:
                continue   # explains its parents, never summed (LED-23), or repeats one
            spread(SHIP_MAP.get(ship, "unmapped_fee"), pence(amount), ship)


def _post_statement(conn, shop_id: str, client: Client, s: dict[str, Any], tally: Tally) -> None:
    posted = conn.execute(
        "select s.id from settlements s where s.shop_id = %s and s.tiktok_statement_id = %s "
        "and exists (select 1 from ledger_entries le where le.settlement_id = s.id "
        "            and le.category = 'settlement')", (shop_id, s["id"])).fetchone()
    if posted:
        # Posted once already. The ledger is not touched again; only what TikTok may still
        # change about the payment is brought up to date.
        conn.execute("update settlements set payment_status = %s, tiktok_payment_id = %s, "
                     "paid_at = %s where id = %s",
                     (s.get("payment_status"), s.get("payment_id"), utc(s.get("payment_time")), posted[0]))
        return

    path = STATEMENT_TXNS_PATH.format(id=s["id"])
    pages = list(client.pages("GET", path, {"sort_field": "order_create_time", "sort_order": "ASC"}))
    head = pages[0] if pages else {}
    transactions = [t for page in pages for t in page.get("transactions") or []]
    currency = s.get("currency") or "GBP"
    statement_time = utc(s["statement_time"])
    settlement_month = london_month(statement_time)
    sid = conn.execute(
        "insert into settlements (shop_id, tiktok_statement_id, statement_amount_minor, currency, "
        "payment_status, tiktok_payment_id, paid_at, statement_time, net_sales_minor, fee_minor, "
        "shipping_cost_minor, adjustment_minor, payable_amount_minor, total_reserve_amount_minor) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "on conflict (shop_id, tiktok_statement_id) do update set payment_status = excluded.payment_status "
        "returning id::text",
        (shop_id, s["id"], pence(s.get("settlement_amount"), currency), currency,
         s.get("payment_status"), s.get("payment_id"), utc(s.get("payment_time")), statement_time,
         pence(s.get("net_sales_amount"), currency), pence(s.get("fee_amount"), currency),
         pence(s.get("shipping_cost_amount"), currency), pence(s.get("adjustment_amount"), currency),
         pence(head.get("payable_amount"), currency) if head.get("payable_amount") is not None else None,
         pence(head.get("total_reserve_amount"), currency)
         if head.get("total_reserve_amount") is not None else None)).fetchone()[0]
    p = _Poster(conn, shop_id, sid, s["id"], settlement_month, tally)

    order_refs = [t["order_id"] for t in transactions if t.get("type") == "ORDER" and t.get("order_id")]
    ids = ensure_orders(conn, shop_id, client, sorted(set(order_refs)))
    for tiktok_order in dict.fromkeys(order_refs):
        order_id = ids.get(tiktok_order)
        if order_id is None:
            raise TikTokError("no_order", f"TikTok returned no order {tiktok_order}")
        calc = client.call("GET", ORDER_CALC_PATH.format(id=tiktok_order))
        _post_order(p, conn, order_id, tiktok_order, calc)
        conn.execute(
            "insert into order_settlements (order_id, shop_id, status, settlement_id) "
            "values (%s, %s, 'settled', %s) on conflict (order_id) do update set "
            "status = 'settled', settlement_id = excluded.settlement_id, updated_at = now()",
            (order_id, shop_id, sid))

    # Adjustments and reserves, from the statement's own transactions, as the ingester does.
    for t in transactions:
        kind = t.get("type")
        if kind == "ORDER":
            continue
        if kind == "RESERVE":
            amount = pence(t.get("reserve_amount"), currency)
            named = ids.get(t.get("associated_order_id")) if t.get("associated_order_id") else None
            p.post("reserve_withheld" if amount < 0 else "reserve_released", amount, statement_time,
                   f"{s['id']}:{t.get('reserve_id') or t.get('id')}", order_id=named,
                   fee_type="reserve_amount", counted=False)
            continue
        amount = pence(t.get("adjustment_amount"), currency)
        named = None
        if t.get("adjustment_order_id"):
            named = ensure_orders(conn, shop_id, client, [t["adjustment_order_id"]]).get(t["adjustment_order_id"])
        p.post("platform_adjustment", amount, statement_time,
               f"{s['id']}:{t.get('adjustment_id') or t.get('id')}", order_id=named, fee_type=kind)
        if amount:
            conn.execute(
                "insert into discrepancies (shop_id, kind, entity_type, entity_id, field, "
                "tiktok_value, applied_value, status, note) "
                "values (%s, 'amount', 'settlement', %s, 'adjustment_amount', %s, %s, 'open', %s)",
                (shop_id, sid, t.get("adjustment_amount"), t.get("adjustment_amount"),
                 f"TikTok recorded this under the type "
                 f"\"{str(kind or 'adjustment').replace('_', ' ').lower()}\" "
                 f"and gave no further reason."))
    p.post("settlement", -p.total, statement_time, s["id"], counted=False)


def sync_finance(conn, shop_id: str, client: Client, since: datetime, until: datetime) -> Tally:
    tally = Tally()
    query = {"sort_field": "statement_time", "sort_order": "ASC",
             "statement_time_ge": str(int(since.timestamp())),
             "statement_time_lt": str(int(until.timestamp()))}
    for page in client.pages("GET", STATEMENTS_PATH, query):
        for s in page.get("statements") or []:
            tally.read += 1
            if (s.get("currency") or "GBP") not in MINOR_UNIT_EXPONENT:
                tally.failed += 1
                tally.notes.append(f"statement {s['id']}: currency {s.get('currency')} is not read")
                continue
            try:
                # A savepoint per statement. One that fails leaves nothing behind, and the
                # others in the run still land, which is what makes a run partial, not failed.
                with conn.transaction():
                    _post_statement(conn, shop_id, client, s, tally)
            except TikTokError as err:
                tally.failed += 1
                tally.notes.append(f"statement {s['id']}: {err}")
    return tally


# --- the first read of a shop ----------------------------------------------------------------

def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def notify_first_read(conn, shop_id, account_id, result: dict[str, Any]) -> bool:
    """One notice when a newly connected shop's first read has finished. Inside `tenant()`.

    Added 9 October 2026 and called only from `connections._first_sync`, so the daily read
    never sends it. The dedupe key names the shop, so a shop that is connected again is not
    told twice. Nothing is sent when the read failed, was skipped or raised: only when every
    domain finished `completed` or `partial`. Returns whether a notice was written.

    A partial read is told that some records were not read and that the daily read does not
    go back for older ones. That is what `window` does, and it was checked by running on
    9 October 2026: a statement from August that failed in the first read was still missing
    after the next daily read, because each later read starts three days before the last one
    ended.
    """
    sync = result.get("sync")
    if "error" in result or not isinstance(sync, dict) or not sync:
        return False
    if any(s not in ("completed", "partial") for s in sync.values()):
        return False
    name, orders, returns, payouts = conn.execute(
        "select coalesce(nullif(s.shop_name, ''), 'your TikTok Shop'), "
        "(select count(*) from orders where shop_id = s.id), "
        "(select count(*) from returns where shop_id = s.id), "
        "(select count(*) from settlements where shop_id = s.id) "
        "from shops s where s.id = %s", (str(shop_id),)).fetchone()
    if orders + returns + payouts == 0:
        body = ("TikTok holds no orders, returns or payouts for this shop yet. MyShopEdge reads "
                "the shop again every day, and your screens fill as they arrive.")
    else:
        body = (f"MyShopEdge read {_count(orders, 'order', 'orders')}, "
                f"{_count(returns, 'return', 'returns')} and {_count(payouts, 'payout', 'payouts')} "
                "from TikTok. Money and Payouts now show them, and an order counts in your "
                "figures once TikTok has paid it out.")
    if "partial" in sync.values():
        body += (" Some records could not be read this time. The daily read looks again only "
                 "at the last three days, so a record older than that may not be read again.")
    row = conn.execute(
        "insert into notifications (account_id, shop_id, type, severity, title, body, "
        "entity_type, entity_id, dedupe_key) values (%s, %s, 'first_read_complete', 'info', "
        "%s, %s, 'shop', %s, %s) on conflict (account_id, dedupe_key) do nothing returning id",
        (str(account_id), str(shop_id), f"MyShopEdge has finished reading {name}.", body,
         str(shop_id), f"first_read_complete:{shop_id}")).fetchone()
    return row is not None


# --- one shop --------------------------------------------------------------------------------

# --- stock -----------------------------------------------------------------------------------

def _absorb(conn, shop_id: str, sku_id: str, title: str, before: int, after: int,
            adjusted: int, tolerance: int, tally: Tally) -> int:
    """STK-8 (A4.1). Returns the adjustment left once a rise in TikTok's count is absorbed.

    Nothing writes a stock movement that would explain a rise (a cancellation restoring stock,
    a purchase), so every rise counts as unexplained. A rise above the seller's tolerance is a
    restock rather than a duplicate: it flows through and raises a discrepancy instead.
    """
    rise = after - before
    if rise <= 0 or adjusted <= 0:
        return adjusted
    if rise > tolerance:
        conn.execute(
            "insert into discrepancies (shop_id, kind, entity_type, entity_id, field, "
            "tiktok_value, seller_value, applied_value, status, note) "
            "values (%s, 'amount', 'sku', %s, 'tiktok_stock', %s, %s, %s, 'open', %s)",
            (shop_id, sku_id, str(after), str(before + adjusted), str(after + adjusted),
             f"TikTok's stock count rose by {rise}. That is more than the {tolerance} units "
             f"MyShopEdge treats as a repeat of your own adjustment of {adjusted}, so both "
             "changes were kept. Count the stock you hold to check which is right."))
        tally.notes.append(f"{sku_id}: rise of {rise} above tolerance {tolerance}")
        return adjusted
    absorbed = min(rise, adjusted)
    on_shelf = after + adjusted - absorbed
    conn.execute(
        "insert into stock_movements (shop_id, sku_id, movement_type, quantity, reason) "
        "values (%s, %s, 'adjustment_absorbed', %s, %s)",
        (shop_id, sku_id, absorbed,
         f"TikTok's count rose from {before} to {after}, so your adjustment was reduced "
         f"from {adjusted} to {adjusted - absorbed}."))
    account = conn.execute("select account_id from shops where id = %s", (shop_id,)).fetchone()[0]
    unit = "unit" if absorbed == 1 else "units"
    them = "it" if absorbed == 1 else "them"
    conn.execute(
        "insert into notifications (account_id, shop_id, type, severity, title, body, "
        "entity_type, entity_id, dedupe_key) values (%s, %s, 'stock_absorbed', 'info', %s, %s, "
        "'sku', %s, %s) on conflict (account_id, dedupe_key) do nothing",
        (str(account), shop_id,
         f"TikTok's count for {title} rose by {rise} {'unit' if rise == 1 else 'units'}.",
         f"You had already added {absorbed} {unit} in MyShopEdge, so MyShopEdge removed "
         f"{them} from your adjustment to avoid counting {them} twice. Stock on hand is "
         f"{on_shelf}.",
         sku_id, f"stock_absorbed:{sku_id}:{datetime.now(timezone.utc).date().isoformat()}"))
    return adjusted - absorbed


def sync_inventory(conn, shop_id: str, client: Client, since: datetime, until: datetime) -> Tally:
    """TikTok's own stock count for every variant MyShopEdge knows, through Inventory Search.

    The shape is the one TikTok returned for My ShopEdge on 30 September 2026 (A32):
    `data.inventory[].skus[]` with `id`, `total_available_quantity` and
    `total_committed_quantity`. `tiktok_stock` takes the available quantity, so a sale lowers
    it as soon as TikTok does. `sold_not_posted` takes the committed quantity, which is
    **unverified** in meaning: the real answer carried 0, with no open order to test it against.

    Only variants MyShopEdge has already read from an order are asked about, because the
    product listing that would name the others has not been called. A variant TikTok answers
    for that is not stored is counted and skipped.
    """
    tally = Tally()
    tolerance = conn.execute(
        "select coalesce((select absorption_tolerance_units from alert_settings where shop_id = %s), 20)",
        (shop_id,)).fetchone()[0]
    products = [r[0] for r in conn.execute(
        "select tiktok_product_id from products where shop_id = %s order by tiktok_product_id",
        (shop_id,)).fetchall()]
    for i in range(0, len(products), INVENTORY_MAX_PRODUCTS):
        batch = products[i:i + INVENTORY_MAX_PRODUCTS]
        data = client.call("POST", INVENTORY_SEARCH_PATH, body={"product_ids": batch})
        for product in data.get("inventory") or []:
            for sku in product.get("skus") or []:
                tally.read += 1
                available = sku.get("total_available_quantity")
                if available is None:
                    tally.failed += 1
                    tally.notes.append(f"{sku.get('id')}: no total_available_quantity")
                    continue
                known = conn.execute(
                    "select k.id, coalesce(nullif(p.title, ''), k.seller_sku, 'this product') "
                    "from skus k join products p on p.id = k.product_id "
                    "where k.shop_id = %s and k.tiktok_sku_id = %s",
                    (shop_id, str(sku.get("id")))).fetchone()
                if known is None:
                    tally.notes.append(f"{sku.get('id')}: not a variant MyShopEdge has read")
                    continue
                sku_id, title = str(known[0]), known[1]
                committed = int(sku.get("total_committed_quantity") or 0)
                row = conn.execute(
                    "select tiktok_stock, adjusted_delta from stock_positions where sku_id = %s",
                    (sku_id,)).fetchone()
                if row is None:
                    conn.execute(
                        "insert into stock_positions (sku_id, shop_id, tiktok_stock, "
                        "sold_not_posted, as_of) values (%s, %s, %s, %s, now())",
                        (sku_id, shop_id, int(available), committed))
                else:
                    before, adjusted = int(row[0]), int(row[1])
                    adjusted = _absorb(conn, shop_id, sku_id, title, before, int(available),
                                       adjusted, tolerance, tally)
                    conn.execute(
                        "update stock_positions set tiktok_stock = %s, adjusted_delta = %s, "
                        "sold_not_posted = %s, as_of = now() where sku_id = %s",
                        (int(available), adjusted, committed, sku_id))
                tally.written += 1
    return tally


DOMAINS = (("orders", sync_orders), ("returns", sync_returns), ("finance", sync_finance),
           ("inventory", sync_inventory))


def sync_shop(conn, shop_id: UUID | str, client: Client, since: datetime, until: datetime,
              kind: str = "incremental") -> dict[str, str]:
    """Orders, returns, statements, then stock, each recorded in `sync_runs`. Inside `tenant()`."""
    shop = str(shop_id)
    outcome: dict[str, str] = {}
    for domain, run in DOMAINS:
        run_id = conn.execute(
            "insert into sync_runs (shop_id, kind, domain, status, cursor, attempt, started_at) "
            "values (%s, %s, %s, 'fetching', %s, 1, now()) returning id",
            (shop, kind, domain, Jsonb({"since": since.isoformat(), "until": until.isoformat()}))).fetchone()[0]
        try:
            with conn.transaction():
                tally = run(conn, shop, client, since, until)
        except TikTokError as err:
            # Which TikTok codes mean the token no longer works is not recorded anywhere in
            # this repository, so only a missing connection is read as needing a reconnect.
            # Every TikTok refusal is `failed`, with TikTok's own code kept in `error`.
            status = "needs_reconnect" if err.code == "no_connection" else "failed"
            conn.execute("update sync_runs set status = %s, finished_at = now(), error = %s where id = %s",
                         (status, Jsonb({"code": err.code, "message": err.message}), run_id))
            outcome[domain] = status
            continue
        status = "partial" if tally.failed else "completed"
        conn.execute(
            "update sync_runs set status = %s, finished_at = now(), records_read = %s, "
            "records_written = %s, records_failed = %s, error = %s where id = %s",
            (status, tally.read, tally.written, tally.failed,
             Jsonb({"notes": tally.notes[:50]}) if tally.notes else None, run_id))
        outcome[domain] = status
    if all(s in ("completed", "partial") for s in outcome.values()):
        conn.execute("update shops set connection_status = 'connected', last_synced_at = now(), "
                     "first_synced_at = coalesce(first_synced_at, now()) where id = %s", (shop,))
    return outcome


# --- every due shop --------------------------------------------------------------------------

# A11.4: TikTok holds data from 1 July 2023. A16.2: twenty four months on every plan. A first
# run reads back to the later of the two. Whether TikTok really returns twenty four months is
# open (A17.3, A19.3).
EARLIEST = datetime(2023, 7, 1, tzinfo=timezone.utc)
HISTORY_DAYS = 730
# Each later run starts three days before the last one ended, so a record TikTok stamped late
# is still read. Everything written is idempotent, so reading a record twice changes nothing.
OVERLAP_DAYS = 3


def window(conn, shop_id: str, now: datetime) -> tuple[datetime, datetime, str]:
    from datetime import timedelta

    last = conn.execute(
        "select max((cursor->>'until')::timestamptz) from sync_runs "
        "where shop_id = %s and status in ('completed', 'partial')", (shop_id,)).fetchone()[0]
    if last is None:
        return max(EARLIEST, now - timedelta(days=HISTORY_DAYS)), now, "backfill"
    return last - timedelta(days=OVERLAP_DAYS), now, "incremental"


def run_due(transport=None, now: datetime | None = None) -> list[dict[str, Any]]:
    """Refresh and sync every shop `shops_due_for_sync()` lists (0027). One shop at a time,
    each in its own `tenant()` transaction, so one shop's failure touches no other."""
    from .db import tenant, unscoped
    from .tiktok_api import client_for, http_transport, refresh_connection

    transport = transport or http_transport
    now = now or datetime.now(timezone.utc)
    with unscoped() as conn:
        due = conn.execute("select shop_id, account_id from shops_due_for_sync()").fetchall()
    return [run_one(shop_id, account_id, transport, now, refresh_connection, client_for, tenant)
            for shop_id, account_id in due]


def run_one(shop_id, account_id, transport=None, now: datetime | None = None,
            refresh_connection=None, client_for=None, tenant=None) -> dict[str, Any]:
    """Refresh and sync one shop, as the daily run does for each due shop.

    Also run in the background straight after a shop connects (connections.tiktok_callback),
    so a new seller's figures start arriving within minutes rather than at the next 05:47 UTC
    run. Added 8 October 2026: the connection screen said "We are reading your orders,
    returns and payouts now" while nothing was. Never raises; a fault is returned in "error".
    """
    from .db import tenant as _tenant
    from .tiktok_api import client_for as _client_for, http_transport
    from .tiktok_api import refresh_connection as _refresh

    transport = transport or http_transport
    now = now or datetime.now(timezone.utc)
    refresh_connection = refresh_connection or _refresh
    client_for = client_for or _client_for
    tenant = tenant or _tenant
    result: dict[str, Any] = {"shop_id": str(shop_id)}
    try:
        with tenant(account_id) as conn:
            result["refresh"] = refresh_connection(conn, shop_id, now, transport)
        with tenant(account_id) as conn:
            status = conn.execute("select connection_status from shops where id = %s",
                                  (str(shop_id),)).fetchone()[0]
            if status == "needs_reconnect":
                result["sync"] = "skipped: needs_reconnect"
            else:
                since, until, kind = window(conn, str(shop_id), now)
                client = client_for(conn, shop_id, transport)
                result["sync"] = sync_shop(conn, shop_id, client, since, until, kind)
    except Exception as err:  # noqa: BLE001  one shop's fault must not stop the others
        result["error"] = f"{type(err).__name__}: {err}"
    return result
