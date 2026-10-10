"""Products, ranked by what the seller actually keeps.

This is the screen the product is named for. A2 specifies the per-product grid and A4
specifies the arithmetic, which is reproduced here verbatim rather than reinvented:

    Return Loss              = -( return_cost entries + write_off entries )
    Cost of goods retained   = product cost x ( units sold - units returned )
    Contribution             = Net Proceeds - Cost of goods retained
    You keep                 = Contribution - Return Loss

Three things in that are easy to get wrong and are handled deliberately.

**A returned unit's cost is never counted twice.** A4.1 records the defect. If a unit came
back resellable its cost sits in stock, and if it came back unsellable its cost is a
write-off inside Return Loss. So the cost carried here is the cost of units sold and not
returned, computed per SKU because cost is a SKU-level fact.

**`kept` is null rather than wrong when a cost is missing.** A product with no uploaded cost
cannot have a Contribution, and showing gross sales in that column would read as profit.
`cost_known` says which it is and `kept_reason` says why in words the seller can act on.

**The rows do not have to add up to the shop total, so `others` exists.** A top ten table
whose rows sum to less than the money screen looks like lost money. `total` is every
product and `others` is what the unshown ones came to, so the arithmetic is visibly closed.

Cost of goods is read from `product_costs` rather than from the `cost_of_goods_sold` ledger
entries, because those are posted for every unit sold including the ones that came back.
A4's formula is explicit that retained cost excludes returned units.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from . import stock
from .auth import Account, require_account
from .dates import business_today
from .db import tenant
from .money import Money, money, per_unit
from .money_lines import SHARED, line_label
from .settlements import MAX_LIMIT, decode_cursor, encode_cursor
from .shops import require_shop
from .stock import StockPosition

router = APIRouter(tags=["Products"])

# Net Proceeds is sales, refunds and platform deductions. It deliberately excludes
# return_cost and write_off, which A4 carries separately through Return Loss, and excludes
# cost_of_goods_sold, which is the seller's own money rather than TikTok's arithmetic.
NET_PROCEEDS_TYPES = ("sale", "refund", "platform_deduction")
RETURN_LOSS_TYPES = ("return_cost", "write_off")

MEASURES = {
    "kept": "kept_minor",
    "net_proceeds": "net_proceeds_minor",
    "gross_sales": "gross_sales_minor",
    "units": "units_sold",
    "returns": "returns_units",
}


class Period(BaseModel):
    from_: date
    to: date
    basis: str

    def model_dump(self, **kw):  # the contract names it `from`, which Python will not
        d = super().model_dump(**kw)
        d["from"] = d.pop("from_")
        return d


class ProductRow(BaseModel):
    product_id: UUID
    tiktok_product_id: str | None = None
    title: str | None = None
    units: int
    gross_sales: Money
    net_proceeds: Money
    kept: Money | None = None
    kept_reason: str | None = None
    returns_units: int = 0
    cost_known: bool = False


class Others(BaseModel):
    count: int
    amount: Money


class Unattributed(BaseModel):
    amount: Money
    lines: list[Any]


class ProductRanking(BaseModel):
    period: dict[str, Any]
    measure: str
    products: list[ProductRow]
    total: Money
    shown_total: Money
    others: Others | None = None
    unattributed: Unattributed | None = None
    shop_total: Money | None = None
    next_cursor: str | None = None


# Money in the period that belongs to the shop and to no variant, such as a platform
# adjustment TikTok applies to a whole statement. The per-product query joins on sku_id, so
# it cannot see these entries, and without them the products screen does not add up to the
# money screen. Ruled by the owner on 25 September 2026: they are shown on their own line.
UNATTRIBUTED_SQL = """
select le.category, le.tiktok_fee_type,
       sum(le.amount_minor) as amount_minor,
       coalesce(max(le.currency), 'GBP') as currency
  from ledger_entries le
 where le.shop_id = %(shop)s
   and {date_column} >= %(from)s
   and {date_column} <= %(to)s
   and le.sku_id is null
   and le.category = any(%(categories)s)
 group by le.category, le.tiktok_fee_type
having sum(le.amount_minor) <> 0
 order by le.category, le.tiktok_fee_type
"""


def _measure_categories(measure: str) -> list[str]:
    """The money screen's categories behind the figure this ranking totals.

    Read from `money_view.CHAIN` so the two screens cannot disagree about what a figure
    contains. Imported here rather than at the top because money_view imports this module.
    """
    from .money_view import CHAIN

    if measure == "gross_sales":
        return ["gross_sales"]
    upto = "refunds" if measure == "net_proceeds" else "return_costs"
    categories: list[str] = []
    for key, _label, _reached, cats in CHAIN:
        categories.extend(cats)
        if key == upto:
            break
    return categories


# One row per product. Every figure is derived here rather than in Python, so the database
# does the arithmetic once instead of the service doing it per row.
SQL = """
with scoped as (
  select le.*, s.product_id
    from ledger_entries le
    join skus s on s.id = le.sku_id
   where le.shop_id = %(shop)s
     and {date_column} >= %(from)s
     and {date_column} <= %(to)s
),
led as (
  select product_id,
         coalesce(sum(amount_minor) filter (where entry_type = any(%(np)s)), 0) as net_proceeds_minor,
         coalesce(sum(amount_minor) filter (where entry_type = any(%(rl)s)), 0) as return_entries_minor,
         coalesce(sum(amount_minor) filter (where category = 'gross_sales'), 0) as gross_sales_minor,
         coalesce(max(currency), 'GBP') as currency
    from scoped group by product_id
),
-- Units follow the same period and basis as the money, because a unit counted in one
-- month and its money in another is how a per-product table stops reconciling.
-- Each sold line carries the London date of its order, because a unit is costed at the cost
-- in force on the day it sold (A31.4, the owner's ruling of 29 September 2026 on fault 10).
sold_lines as (
  select s.product_id, s.id as sku_id, ol.quantity,
         (o.order_created_at at time zone 'Europe/London')::date as sale_day
    from (select distinct order_line_id from scoped where category = 'gross_sales'
           and order_line_id is not null) g
    join order_lines ol on ol.id = g.order_line_id
    join orders o on o.id = ol.order_id
    join skus s on s.id = ol.sku_id
),
sold as (
  select product_id, sku_id, sum(quantity) as units from sold_lines group by product_id, sku_id
),
-- A returned item is dated by its refund for the period, and costed at the date of the
-- order it came back from, so a return takes off exactly the cost its sale put on.
returned_items as (
  select s.product_id, s.id as sku_id, ri.quantity,
         (o.order_created_at at time zone 'Europe/London')::date as sale_day
    from return_items ri
    join returns r on r.id = ri.return_id
    join orders o on o.id = r.order_id
    join skus s on s.id = ri.sku_id
   where ri.shop_id = %(shop)s
     -- The London date, A29.9. A bare ::date gives the database session's date, which is
     -- UTC, so a return refunded between midnight and one in the morning in summer was
     -- counted in the previous day. returns.py counts the same way.
     and (coalesce(r.refund_completed_at, r.requested_at) at time zone 'Europe/London')::date >= %(from)s
     and (coalesce(r.refund_completed_at, r.requested_at) at time zone 'Europe/London')::date <= %(to)s
),
returned as (
  select product_id, sku_id, sum(quantity) as units from returned_items group by product_id, sku_id
),
-- The cost in force on each unit's sale date (A31.4). A cost entered today does not rewrite
-- a past sale, as the contract requires (CST-4), and a month before any cost took effect
-- stays unknown however long a period it is read in. Superseded rows are read too, because
-- superseded_at records when a row was replaced, not the business date a cost stopped
-- applying. Two rows can share one effective_from when a seller corrects a cost on the day
-- they entered it, so created_at breaks the tie and the later entry wins, as
-- `returns.check_return_item` does for a write-off.
sold_cost as (
  select sl.sku_id, sl.product_id, sum(c.cost_minor * sl.quantity) as cost_minor,
         bool_or(c.cost_minor is null) as missing
    from sold_lines sl
    left join lateral (
      select pc.cost_minor from product_costs pc
       where pc.shop_id = %(shop)s and pc.sku_id = sl.sku_id and pc.effective_from <= sl.sale_day
       order by pc.effective_from desc, pc.created_at desc limit 1) c on true
   group by sl.sku_id, sl.product_id
),
returned_cost as (
  select ri.sku_id, sum(c.cost_minor * ri.quantity) as cost_minor,
         bool_or(c.cost_minor is null) as missing
    from returned_items ri
    left join lateral (
      select pc.cost_minor from product_costs pc
       where pc.shop_id = %(shop)s and pc.sku_id = ri.sku_id and pc.effective_from <= ri.sale_day
       order by pc.effective_from desc, pc.created_at desc limit 1) c on true
   group by ri.sku_id
),
-- A4: retained cost is the cost of what sold less the cost of what came back, per SKU,
-- floored at zero because more returns than sales in a period is possible at a month
-- boundary and negative cost is not. A variant is uncosted when any unit it sold, or any
-- unit returned against it, had no cost on its sale date.
retained as (
  select sc.product_id,
         sum(greatest(sc.cost_minor - coalesce(rc.cost_minor, 0), 0)) as cost_retained_minor,
         count(*) filter (where sc.missing or coalesce(rc.missing, false)) as skus_without_cost
    from sold_cost sc
    left join returned_cost rc on rc.sku_id = sc.sku_id
   group by sc.product_id
),
units as (
  select product_id, sum(units) as units_sold from sold group by product_id
),
rets as (
  select product_id, sum(units) as returns_units from returned group by product_id
)
select p.id as product_id, p.tiktok_product_id, p.title,
       coalesce(u.units_sold, 0) as units_sold,
       coalesce(rr.returns_units, 0) as returns_units,
       led.gross_sales_minor, led.net_proceeds_minor, led.currency,
       -- Return Loss is positive money lost. Both entry types are negative in the ledger.
       -led.return_entries_minor as return_loss_minor,
       rt.cost_retained_minor,
       coalesce(rt.skus_without_cost, 0) as skus_without_cost,
       case when coalesce(rt.skus_without_cost, 1) = 0
            then led.net_proceeds_minor - rt.cost_retained_minor + led.return_entries_minor
       end as kept_minor
  from led
  join products p on p.id = led.product_id
  left join units u on u.product_id = led.product_id
  left join rets rr on rr.product_id = led.product_id
  left join retained rt on rt.product_id = led.product_id
"""


@router.get("/shops/{shopId}/products", response_model=ProductRanking)
def list_products(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    basis: Annotated[str, Query(pattern="^(sales|cash)$")] = "sales",
    period_from: Annotated[date | None, Query(alias="from")] = None,
    period_to: Annotated[date | None, Query(alias="to")] = None,
    measure: Annotated[str, Query(pattern="^(kept|net_proceeds|gross_sales|units|returns)$")] = "kept",
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> ProductRanking:
    today = business_today()
    start = period_from or today.replace(day=1)
    end = period_to or today

    date_column = "le.basis_day" if basis == "sales" else "le.settlement_month"
    sql = SQL.format(date_column=date_column)
    args = {
        "shop": str(shop_id),
        "from": start,
        "to": end,
        "np": list(NET_PROCEEDS_TYPES),
        "rl": list(RETURN_LOSS_TYPES),
    }

    with tenant(account.id) as conn:
        cur = conn.execute(sql, args)
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
        cur = conn.execute(
            UNATTRIBUTED_SQL.format(date_column=date_column),
            {**args, "categories": _measure_categories(measure)},
        )
        cols = [d.name for d in cur.description]
        loose = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]

    currency = rows[0]["currency"] if rows else (loose[0]["currency"] if loose else "GBP")

    # Ranking happens here rather than in SQL because `kept` can be null, and a null sorts
    # unpredictably across databases. A product with an unknown cost ranks last on `kept`
    # rather than first, which is what a seller would expect.
    column = MEASURES[measure]
    def sort_key(r: dict[str, Any]):
        v = r.get(column)
        return (v is None, -(v or 0))

    rows.sort(key=sort_key)

    # The total is every product, computed before the page is cut.
    total_minor = sum(
        (r[column] or 0) if column not in ("units_sold", "returns_units") else 0
        for r in rows
    )
    if column in ("units_sold", "returns_units"):
        # A count is not money. The contract still requires a Money total, so it carries
        # the kept figure, which is the money a units ranking is ultimately about.
        total_minor = sum(r["kept_minor"] or 0 for r in rows)

    offset = 0
    if cursor:
        _, raw = decode_cursor(cursor)
        offset = int(raw)

    page = rows[offset:offset + limit]
    next_cursor = (
        encode_cursor_offset(offset + limit) if offset + limit < len(rows) else None
    )

    products = [
        ProductRow(
            product_id=r["product_id"],
            tiktok_product_id=r["tiktok_product_id"],
            title=r["title"],
            units=int(r["units_sold"]),
            gross_sales=money(int(r["gross_sales_minor"]), currency),
            net_proceeds=money(int(r["net_proceeds_minor"]), currency),
            kept=money(int(r["kept_minor"]), currency) if r["kept_minor"] is not None else None,
            kept_reason=(
                None if r["kept_minor"] is not None
                else (
                    "One variant had no cost price on the day some of its units sold, so "
                    "gross profit after returns for this period is not known."
                    if int(r["skus_without_cost"]) == 1
                    else f"{int(r['skus_without_cost'])} variants had no cost price on the day "
                         "some of their units sold, so gross profit after returns for this "
                         "period is not known."
                )
            ),
            returns_units=int(r["returns_units"]),
            cost_known=r["kept_minor"] is not None,
        )
        for r in page
    ]

    shown_minor = sum(
        (r["kept_minor"] or 0) if column in ("units_sold", "returns_units") else (r[column] or 0)
        for r in page
    )
    unshown = [r for r in rows if r not in page]

    from .money_view import _line

    loose_lines = [_line(r, currency) for r in loose]
    loose_minor = sum(int(r["amount_minor"]) for r in loose)
    # Every total except gross sales and net proceeds is built from `kept`, which is null for
    # a product with no cost price. The shop's figure is then not known, so none is given.
    kept_based = column not in ("gross_sales_minor", "net_proceeds_minor")
    shop_known = not (kept_based and any(r["kept_minor"] is None for r in rows))

    return ProductRanking(
        period={"from": start.isoformat(), "to": end.isoformat(), "basis": basis},
        measure=measure,
        products=products,
        total=money(int(total_minor), currency),
        shown_total=money(int(shown_minor), currency),
        others=(
            Others(
                count=len(unshown),
                amount=money(int(total_minor - shown_minor), currency),
            )
            if unshown else None
        ),
        unattributed=(
            Unattributed(amount=money(loose_minor, currency), lines=loose_lines)
            if loose_lines else None
        ),
        shop_total=money(int(total_minor) + loose_minor, currency) if shop_known else None,
        next_cursor=next_cursor,
    )


def encode_cursor_offset(offset: int) -> str:
    """Offset rather than keyset, and the reason is worth stating.

    `settlements.py` uses keyset pagination because a settlement list changes under the
    caller as new statements arrive. A product ranking is computed over a closed period and
    re-sorted in Python on every request, so there is no stable key to page by. The offset
    is honest about that rather than pretending to a guarantee it cannot make.
    """
    from datetime import datetime, timezone
    return encode_cursor(datetime.now(timezone.utc), str(offset))


# ---------------------------------------------------------------- one product

class CalculatorLine(BaseModel):
    label: str
    amount: Money
    category: str | None = None
    tiktok_fee_type: str | None = None


class CalculatorSection(BaseModel):
    key: str
    label: str
    lines: list[CalculatorLine]
    subtotal: Money
    subtotal_label: str | None = None


class SkuRow(BaseModel):
    sku_id: UUID
    tiktok_sku_id: str | None = None
    seller_sku: str | None = None
    variant_label: str | None = None
    cost: Money | None = None


class ProductDetail(BaseModel):
    product: ProductRow
    period: dict[str, Any]
    per_unit: dict[str, Any]
    sections: list[CalculatorSection]
    stock: StockPosition | None = None
    skus: list[SkuRow] = []


# A8: every line carries TikTok's own name or the correct accounting term, never invented
# shorthand, and nothing is merged. The section a category belongs to is a presentation
# decision; the labels below are the terminology standard's, not new coinages.
# The sections follow A4's chain exactly, because the calculator has to arrive at the same
# You keep the ranking shows. A first attempt grouped refunds with write-offs and took the
# cost of goods from the ledger, and running it against the Computer Desk gave 900 where
# the headline said 6000. The gap was the returned unit's cost counted twice, which is
# precisely the defect A4.1 records.
#
#   Sales less refunds and deductions  = Net Proceeds
#   less cost of goods retained        = Gross profit
#   less return costs                  = Gross profit after returns
#
# The labels are A8's. Until 24 September this table said "Contribution", "Return Loss" and
# "You keep", all three withdrawn by A8 and forbidden on screen by TC-CLR-06, and the line
# labels differed from the Money calculator's for the same money. Found by rendering the
# product screen, not by reading this file.
#
# cost_of_goods_sold is deliberately absent from these lists. The ledger posts it for every
# unit sold including the ones that came back, so it is replaced by a computed line.
# When a cost is missing, the stages that need it show their own total under these names
# rather than a running "Gross profit" that leaves the cost of goods out. Money does the same
# (money_view.SECTION_TOTALS). Added 8 October 2026 from the copy audit, finding 8.
INCOMPLETE_TOTALS = {"your_costs": "Total your costs", "return_loss": "Total return costs"}

# A8.5 fixes the order for every period, product and export, so the first three stages are
# Money's (money_view.CHAIN): refunds come after TikTok fees, and no subtotal is named that A8
# does not name. Until 9 October 2026 refunds sat in the first stage under "Sales after
# refunds" (copy audit, Area B row 60). Only the stages moved; every line and the figure the
# chain ends on are unchanged.
SECTIONS: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("sales", "Sales", "Net sales", ("gross_sales", "seller_discount")),
    ("deductions", "TikTok fees", "Net proceeds before refunds", (
        "platform_commission", "affiliate_commission", "transaction_fee",
        "smart_promotions_fee", "shipping_fee", "return_handling_fee",
        "fbt_operations_fee", "fbt_shipping_fee", "fbt_storage_fee", "unmapped_fee",
    )),
    ("refunds", "Refunds", "Net proceeds", ("refund",)),
    ("your_costs", "Your costs", "Gross profit", ("seller_shipping",)),
    ("return_loss", "Return costs", "Gross profit after returns",
     ("return_shipping", "stock_written_off")),
]

LABELS = {
    "gross_sales": "Gross sales (GMV)",
    "seller_discount": "Seller discounts",
    "platform_commission": "Platform commission",
    "affiliate_commission": "Affiliate commission",
    "transaction_fee": "Transaction fee",
    "smart_promotions_fee": "Smart Promotions fee",
    "shipping_fee": "Shipping fee",
    "return_handling_fee": "Return handling fee",
    "fbt_operations_fee": "FBT operations fee",
    "fbt_shipping_fee": "FBT shipping fee",
    "fbt_storage_fee": "FBT storage fee",
    "unmapped_fee": "Fee MyShopEdge does not recognise",
    "refund": "Refunds to customers",
    "return_shipping": "Return shipping you paid",
    "stock_written_off": "Stock written off",
    "cost_of_goods_sold": "Cost of goods sold",
    "seller_shipping": "Shipping and packaging you pay",
}


@router.get("/shops/{shopId}/products/{productId}", response_model=ProductDetail)
def get_product(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    productId: UUID,
    basis: Annotated[str, Query(pattern="^(sales|cash)$")] = "sales",
    period_from: Annotated[date | None, Query(alias="from")] = None,
    period_to: Annotated[date | None, Query(alias="to")] = None,
) -> ProductDetail:
    from .problems import Problem

    today = business_today()
    start = period_from or today.replace(day=1)
    end = period_to or today
    date_column = "le.basis_day" if basis == "sales" else "le.settlement_month"

    with tenant(account.id) as conn:
        prod = conn.execute(
            "select id, tiktok_product_id, title from products where id=%s and shop_id=%s",
            (str(productId), str(shop_id)),
        ).fetchone()
        if prod is None:
            # Same answer as another account's product, for the reason in shops.py.
            raise Problem(404, "product_not_found", "That product was not found.")

        # One line per category and fee type. Not merged, so an unmapped fee keeps the
        # name TikTok gave it and a seller can look it up.
        cur = conn.execute(
            f"""select le.category, le.tiktok_fee_type,
                       sum(le.amount_minor) as amount_minor,
                       coalesce(max(le.currency), 'GBP') as currency
                  from ledger_entries le
                  join skus s on s.id = le.sku_id
                 where le.shop_id = %s and s.product_id = %s
                   and {date_column} >= %s and {date_column} <= %s
                 group by le.category, le.tiktok_fee_type
                 having sum(le.amount_minor) <> 0
                 order by le.category, le.tiktok_fee_type""",
            (str(shop_id), str(productId), start, end),
        )
        cols = [d.name for d in cur.description]
        lines = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]

        skus = conn.execute(
            """select s.id, s.tiktok_sku_id, s.seller_sku, s.variant_label,
                      (select cost_minor from product_costs pc
                        where pc.sku_id = s.id and pc.superseded_at is null
                        order by pc.effective_from desc limit 1) as cost_minor
                 from skus s where s.product_id = %s and s.shop_id = %s
                order by s.variant_label nulls last""",
            (str(productId), str(shop_id)),
        ).fetchall()

        stock_rows = stock.positions(conn, shop_id, product_id=productId)

    currency = lines[0]["currency"] if lines else "GBP"

    # The row for this product, from the same query the ranking uses so the list and the
    # detail cannot disagree. A figure that differs between two screens is the defect a
    # seller notices first.
    ranking = list_products(
        account=account, shop_id=shop_id, basis=basis,
        period_from=start, period_to=end, measure="kept", limit=MAX_LIMIT, cursor=None,
    )
    row = next((p for p in ranking.products if str(p.product_id) == str(productId)), None)
    if row is None:
        row = ProductRow(
            product_id=productId, tiktok_product_id=prod[1], title=prod[2],
            units=0, gross_sales=money(0, currency), net_proceeds=money(0, currency),
        )

    # Cost of goods retained, computed rather than read, for the reason above the SECTIONS
    # table. Null when any variant has no cost, which is the same condition that makes
    # `kept` null, so the calculator and the headline agree about what is unknown.
    retained_minor = None
    if row.cost_known:
        retained_minor = (
            row.net_proceeds.amount_minor
            - (row.kept.amount_minor if row.kept else 0)
            - sum(int(l["amount_minor"]) for l in lines
                  if l["category"] in ("return_shipping", "stock_written_off")) * -1
        )

    sections: list[CalculatorSection] = []
    running = 0
    for key, label, subtotal_label, categories in SECTIONS:
        rows = [l for l in lines if l["category"] in categories]
        section_lines = [
            CalculatorLine(
                label=line_label(l["category"], l["tiktok_fee_type"])
                      if l["category"] in ("unmapped_fee", *SHARED)
                      else LABELS.get(l["category"], l["category"]),
                amount=money(int(l["amount_minor"]), currency),
                category=l["category"],
                tiktok_fee_type=l["tiktok_fee_type"],
            )
            for l in rows
        ]
        # The computed cost line sits in Your costs, where a seller looks for it.
        if key == "your_costs" and retained_minor is not None:
            section_lines.insert(0, CalculatorLine(
                label=LABELS["cost_of_goods_sold"],
                amount=money(-retained_minor, currency),
                category="cost_of_goods_sold",
                tiktok_fee_type=None,
            ))
        if not section_lines:
            continue
        own = sum(l.amount.amount_minor for l in section_lines)
        running += own
        incomplete_stage = retained_minor is None and key in INCOMPLETE_TOTALS
        sections.append(CalculatorSection(
            key=key, label=label, lines=section_lines,
            # The subtotal is the running figure, not the section's own sum, because the
            # seller is reading a chain that ends at You keep rather than four unrelated
            # piles. The label names which figure of A4 each stage has reached. When the
            # cost of goods is not known, that figure is not reached, so the stage shows
            # its own total instead.
            subtotal=money(own if incomplete_stage else running, currency),
            subtotal_label=INCOMPLETE_TOTALS[key] if incomplete_stage else subtotal_label,
        ))

    return ProductDetail(
        product=row,
        period={"from": start.isoformat(), "to": end.isoformat(), "basis": basis},
        per_unit={
            "units": max(row.units, 1),
            "sections": [
                CalculatorSection(
                    key=s.key, label=s.label,
                    lines=[
                        CalculatorLine(
                            label=l.label,
                            amount=money(per_unit(l.amount.amount_minor, row.units), currency),
                            category=l.category, tiktok_fee_type=l.tiktok_fee_type,
                        ) for l in s.lines
                    ],
                    # Each figure is the period's figure divided by the units and rounded on
                    # its own, so a subtotal can differ by a penny from the sum of rounded
                    # lines above it. The subtotal is the true per-unit figure.
                    subtotal=money(per_unit(s.subtotal.amount_minor, row.units), currency),
                    subtotal_label=s.subtotal_label,
                ) for s in sections
            ],
        },
        sections=sections,
        # The contract carries one StockPosition and a product can have several SKUs, so a
        # single position is only honest for a single-variant product. For a multi-variant
        # product it is omitted rather than picking one arbitrarily or summing positions
        # that belong to different shelves. Recorded as a contract gap in A25.
        stock=stock_rows[0] if len(stock_rows) == 1 else None,
        skus=[
            SkuRow(
                sku_id=s[0], tiktok_sku_id=s[1], seller_sku=s[2], variant_label=s[3],
                cost=money(int(s[4]), currency) if s[4] is not None else None,
            ) for s in skus
        ],
    )
