"""Rule-based insights with their evidence, `getInsights` (DSH-6). Built 29 September 2026.

The SRD requires "the four MVP insights", and no document in this repository names all four.
The owner ruled on 29 September (A31.1) that the two the documents evidence are built and
the other two stay unbuilt until he names them:

- **`negative_contribution`.** The wireframes say "Negative Contribution shown in full, with
  an insight offering options." Contribution is A4's: Net Proceeds less the cost of the units
  sold and not returned. It is worked out only for a product whose every variant sold in the
  period has a cost, because a contribution without the cost is not a contribution.
- **`postage_share`.** The QA case for DSH-6 reads: "Clay Mask: postage and packing £2.51 on
  £9.25 ... Insight states postage share 27p in the £1; no claim that posting costs more than
  making." The £9.25 is what reached the shop, which the G5 case shows is sales after the
  seller's own discounts and before TikTok's cut. The owner ruled that it is shown for every
  costed product, with no threshold, so no threshold is invented here.

Every figure in the text is one of the figures in `evidence`, as FI-4 requires ("Insight
text contains only values present in the data"). The period is the current London month to
date, the same default as the Products screen, because the contract gives the operation no
period parameter.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from .auth import Account, require_account
from .dates import business_today, now_utc
from .db import tenant
from .money import Money, money
from .products import NET_PROCEEDS_TYPES, RETURN_LOSS_TYPES
from .products import SQL as PRODUCTS_SQL
from .shops import require_shop

router = APIRouter(tags=["Products"])


class EvidenceValue(BaseModel):
    label: str
    amount: Money | None = None
    number: float | None = None


class EvidencePeriod(BaseModel):
    from_: str = Field(serialization_alias="from")
    to: str
    basis: Literal["sales", "cash"]


class Evidence(BaseModel):
    period: EvidencePeriod
    values: list[EvidenceValue]
    entity_type: str | None = None
    entity_id: UUID | None = None


class Insight(BaseModel):
    rule_key: str
    severity: Literal["info", "warning", "critical"]
    headline: str
    detail: str | None = None
    evidence: Evidence


class InsightsOut(BaseModel):
    as_of: str
    insights: list[Insight]


# What reached the shop, per product, and what the seller pays to post and pack the units
# sold. Postage and packing are the seller's own per-unit figures from `product_costs`,
# entered beside the unit cost, which is where the QA case's "postage and packing £2.51"
# sits beside "stock £3.20". The row in force at the period's end is used, with the same
# tie-break as the product figures. A variant sold with neither figure recorded makes the
# product's postage unknown, and no postage insight is given for it.
EXTRA_SQL = """
with scoped as (
  select le.*, s.product_id from ledger_entries le join skus s on s.id = le.sku_id
   where le.shop_id = %(shop)s and {date_column} >= %(from)s and {date_column} <= %(to)s
),
ns as (
  select product_id,
         coalesce(sum(amount_minor) filter (where category in ('gross_sales', 'seller_discount')), 0)
           as net_sales_minor
    from scoped group by product_id
),
sold as (
  select s.product_id, s.id as sku_id, sum(ol.quantity) as units
    from (select distinct order_line_id from scoped where category = 'gross_sales'
           and order_line_id is not null) g
    join order_lines ol on ol.id = g.order_line_id
    join skus s on s.id = ol.sku_id
   group by s.product_id, s.id
),
pc as (
  select distinct on (sku_id) sku_id, packing_minor, postage_minor
    from product_costs where shop_id = %(shop)s and effective_from <= %(to)s
   order by sku_id, effective_from desc, created_at desc
),
pp as (
  select sd.product_id,
         sum((coalesce(pc.packing_minor, 0) + coalesce(pc.postage_minor, 0)) * sd.units) as pp_minor,
         count(*) filter (where pc.packing_minor is null and pc.postage_minor is null)
           as skus_without_pp
    from sold sd left join pc on pc.sku_id = sd.sku_id
   group by sd.product_id
)
select ns.product_id, ns.net_sales_minor, pp.pp_minor, coalesce(pp.skus_without_pp, 1) as skus_without_pp
  from ns left join pp on pp.product_id = ns.product_id
"""


def _pence_in_pound(part: int, whole: int) -> int:
    return int((Decimal(part) * 100 / Decimal(whole)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _pounds(minor: int) -> str:
    return f"£{Decimal(minor) / 100:,.2f}"


def build(rows: list[dict[str, Any]], extra: dict[Any, dict[str, Any]], period: EvidencePeriod,
          currency: str) -> list[Insight]:
    """The insights for one period, from the product rows. Pure, so it is tested directly."""
    out: list[Insight] = []
    for r in rows:
        units = int(r["units_sold"])
        costed = units > 0 and int(r["skus_without_cost"]) == 0 and r["cost_retained_minor"] is not None
        if not costed:
            continue
        name = r["title"] or "A product TikTok did not name"
        net_proceeds = int(r["net_proceeds_minor"])
        cost = int(r["cost_retained_minor"])
        contribution = net_proceeds - cost
        ev_product = {"entity_type": "product", "entity_id": r["product_id"]}

        if contribution < 0:
            out.append(Insight(
                rule_key="negative_contribution", severity="warning",
                headline=f"{name} lost {_pounds(-contribution)} on {units} "
                         f"{'unit' if units == 1 else 'units'} sold this period.",
                detail="What reached you after TikTok's cut was less than the cost of the units "
                       "sold and not returned. Options: check the cost price recorded for it, "
                       "look at its selling price and discounts, or look at what TikTok takes on it.",
                evidence=Evidence(period=period, values=[
                    EvidenceValue(label="Units sold", number=units),
                    EvidenceValue(label="Net proceeds", amount=money(net_proceeds, currency)),
                    EvidenceValue(label="Cost of units sold and not returned", amount=money(-cost, currency)),
                    EvidenceValue(label="Contribution", amount=money(contribution, currency)),
                ], **ev_product),
            ))

        e = extra.get(r["product_id"]) or {}
        net_sales = int(e.get("net_sales_minor") or 0)
        postage = int(e.get("pp_minor") or 0)
        if net_sales > 0 and postage > 0 and int(e.get("skus_without_pp", 1)) == 0:
            pence = _pence_in_pound(postage, net_sales)
            out.append(Insight(
                rule_key="postage_share", severity="info",
                headline=f"Postage and packing took {pence}p of every £1 that reached you for {name}.",
                detail=f"Your postage and packing figures come to {_pounds(postage)} for the units "
                       f"sold, against {_pounds(net_sales)} of sales after your discounts.",
                evidence=Evidence(period=period, values=[
                    EvidenceValue(label="Sales after your discounts", amount=money(net_sales, currency)),
                    EvidenceValue(label="Postage and packing, from your cost figures",
                                  amount=money(-postage, currency)),
                    EvidenceValue(label="Pence in the £1", number=pence),
                ], **ev_product),
            ))
    return out


@router.get("/shops/{shopId}/insights", response_model=InsightsOut,
            summary="Rule-based insights with evidence")
def get_insights(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    basis: Annotated[Literal["sales", "cash"], Query()] = "sales",
) -> InsightsOut:
    today = business_today()
    start, end = today.replace(day=1), today
    date_column = "le.basis_day" if basis == "sales" else "le.settlement_month"
    args = {"shop": str(shop_id), "from": start, "to": end,
            "np": list(NET_PROCEEDS_TYPES), "rl": list(RETURN_LOSS_TYPES)}
    with tenant(account.id) as conn:
        cur = conn.execute(PRODUCTS_SQL.format(date_column=date_column), args)
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
        cur = conn.execute(EXTRA_SQL.format(date_column=date_column), args)
        cols = [d.name for d in cur.description]
        extra = {x["product_id"]: x for x in (dict(zip(cols, r, strict=True)) for r in cur.fetchall())}
    currency = rows[0]["currency"] if rows else "GBP"
    period = EvidencePeriod(from_=start.isoformat(), to=end.isoformat(), basis=basis)
    return InsightsOut(as_of=now_utc().isoformat(), insights=build(rows, extra, period, currency))
