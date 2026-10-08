"""Cost prices. `putSkuCost` and `getCostCoverage`.

A missing cost makes gross profit after returns unknown for that product, and every screen
that shows the figure tells the seller so. These two operations are where the seller acts
on that, one variant at a time.

SETTING A COST NEVER OVERWRITES ONE

The contract (CST-1, CST-4, CST-5) says costs are never overwritten. The current cost is
stamped `superseded_at` and a new row is inserted, inside one transaction. The unique index
`product_costs_current_idx` allows one current cost per variant, so two concurrent writes
cannot both leave a current row: the second fails rather than doubling the cost.

The contract also says a figure calculated last month still reconciles against the cost in
force at the time. Until 28 September the figure queries in `products.py` read only the
current cost, so a new cost changed past months' gross profit too. On 28 September the
owner approved taking Emergent AI's change (commit d87f6a0): the figures and coverage read
the cost in force at the period's end. On 29 September the owner ruled on fault 10 (A31.4)
that each unit is costed at the cost in force on its sale date, by `effective_from`, with
`created_at` as the tie-break for two rows on one day. The figures and coverage follow that
rule, so a cost that changes inside a month applies from its own date onwards. A variant
counts as missing a cost when any unit it sold in the period had no cost on its sale date.

A cost in a currency other than the shop's is refused. `cost_minor` is summed with sales
in the shop's currency, and adding pence to cents would be a wrong figure presented as a
right one.

COVERAGE, CST-6

The contract defines coverage as the share of sold units whose cost is known, over the
period. Units are order line quantities on orders that were not cancelled, dated in
Europe/London (A29.9), the same way `stock.py` counts its pace. The `top_missing` list is
ordered by gross sales, because the contract describes it as the products whose missing
cost suppresses the most figures, and gross sales is the size of the figure suppressed.

Both queries were run on the development branch, 24 September 2026.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field

from .auth import Account, require_account
from .dates import business_today
from .db import tenant
from .money import Money, money
from .problems import Problem
from .shops import require_shop

router = APIRouter(tags=["Costs"])


class CostIn(BaseModel):
    cost: Money
    packing: Money | None = None
    postage: Money | None = None
    effective_from: date | None = None


class ProductCost(BaseModel):
    sku_id: UUID
    cost: Money
    packing: Money | None = None
    postage: Money | None = None
    source: Literal["upload", "manual"]
    effective_from: date
    supersedes: UUID | None = None


class MissingCost(BaseModel):
    sku_id: UUID
    product_title: str | None = None
    units: int = Field(ge=0)
    gross_sales: Money


class CostCoverage(BaseModel):
    period: dict[str, str]
    coverage: float = Field(ge=0, le=1)
    units_with_cost: int = Field(ge=0)
    units_total: int = Field(ge=0)
    skus_missing_cost: int = Field(ge=0)
    top_missing: list[MissingCost]


def _check_amounts(body: CostIn, currency: str) -> None:
    for name, m in (("cost", body.cost), ("packing", body.packing), ("postage", body.postage)):
        if m is None:
            continue
        if m.amount_minor < 0:
            raise Problem(422, "validation_failed", f"The {name} cannot be negative.")
        if m.currency != currency:
            raise Problem(
                422, "validation_failed",
                f"The {name} is in {m.currency} and this shop sells in {currency}. "
                f"Enter it in {currency}.",
            )


@router.put("/shops/{shopId}/skus/{skuId}/cost", response_model=ProductCost)
def put_sku_cost(
    body: CostIn,
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    sku_id: Annotated[UUID, Path(alias="skuId")],
) -> ProductCost:
    effective_from = body.effective_from or business_today()

    with tenant(account.id) as conn:
        shop = conn.execute(
            "select trim(s.currency) from skus k join shops s on s.id = k.shop_id "
            "where k.id = %s and k.shop_id = %s",
            (str(sku_id), str(shop_id)),
        ).fetchone()
        if shop is None:
            # The same answer for a variant on another account, for the reason in shops.py.
            raise Problem(404, "sku_not_found", "That product variant was not found.")
        currency = shop[0]
        _check_amounts(body, currency)

        previous = conn.execute(
            "update product_costs set superseded_at = now() "
            "where sku_id = %s and shop_id = %s and superseded_at is null returning id",
            (str(sku_id), str(shop_id)),
        ).fetchone()
        conn.execute(
            "insert into product_costs (shop_id, sku_id, cost_minor, packing_minor, "
            "postage_minor, currency, source, effective_from, created_by) "
            "values (%s, %s, %s, %s, %s, %s, 'manual', %s, %s)",
            (
                str(shop_id), str(sku_id), body.cost.amount_minor,
                body.packing.amount_minor if body.packing else None,
                body.postage.amount_minor if body.postage else None,
                currency, effective_from, str(account.id),
            ),
        )

    return ProductCost(
        sku_id=sku_id,
        cost=money(body.cost.amount_minor, currency),
        packing=money(body.packing.amount_minor, currency) if body.packing else None,
        postage=money(body.postage.amount_minor, currency) if body.postage else None,
        source="manual",
        effective_from=effective_from,
        supersedes=previous[0] if previous else None,
    )


COVERAGE_SQL = """
with lines as (
  select ol.sku_id, ol.quantity, ol.unit_price_minor,
         exists (select 1 from product_costs pc
                  where pc.shop_id = %(shop)s and pc.sku_id = ol.sku_id
                    and pc.effective_from <= (o.order_created_at at time zone 'Europe/London')::date)
           as has_cost
    from order_lines ol
    join orders o on o.id = ol.order_id
   where ol.shop_id = %(shop)s
     and o.cancelled_at is null
     and (o.order_created_at at time zone 'Europe/London')::date between %(from)s and %(to)s
),
costed as (
  select sku_id, sum(quantity) as units,
         sum(quantity) filter (where has_cost) as units_costed,
         sum(quantity * unit_price_minor) as gross_minor,
         bool_and(has_cost) as has_cost
    from lines group by sku_id
)
select c.sku_id, p.title as product_title, c.units, coalesce(c.units_costed, 0) as units_costed,
       c.gross_minor, c.has_cost,
       (select trim(currency) from shops where id = %(shop)s) as currency
  from costed c
  join skus k on k.id = c.sku_id
  left join products p on p.id = k.product_id
 order by c.has_cost, c.gross_minor desc, c.sku_id
"""


@router.get("/shops/{shopId}/costs/coverage", response_model=CostCoverage)
def get_cost_coverage(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    period_from: Annotated[date | None, Query(alias="from")] = None,
    period_to: Annotated[date | None, Query(alias="to")] = None,
) -> CostCoverage:
    today = business_today()
    start = period_from or today.replace(day=1)
    end = period_to or today
    if start > end:
        raise Problem(422, "validation_failed", "The period ends before it starts. Choose an end date on or after the start date.")

    with tenant(account.id) as conn:
        cur = conn.execute(COVERAGE_SQL, {"shop": str(shop_id), "from": start, "to": end})
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]

    units_total = sum(int(r["units"]) for r in rows)
    units_with_cost = sum(int(r["units_costed"]) for r in rows)
    missing = [r for r in rows if not r["has_cost"]]
    # Coverage is a share, not money, so a float is the contract's own type. With no units
    # sold nothing is uncosted, so the gate is open rather than shut.
    coverage = 1.0 if units_total == 0 else units_with_cost / units_total

    return CostCoverage(
        period={"from": start.isoformat(), "to": end.isoformat(), "basis": "sales"},
        coverage=coverage,
        units_with_cost=units_with_cost,
        units_total=units_total,
        skus_missing_cost=len(missing),
        top_missing=[
            MissingCost(
                sku_id=r["sku_id"], product_title=r["product_title"], units=int(r["units"]),
                gross_sales=money(int(r["gross_minor"]), r["currency"] or "GBP"),
            )
            for r in missing[:10]
        ],
    )


# --- listSkuCosts, for S20 Manual cost entry ---------------------------------------------------
#
# A3 S20 lists every variant with its units sold in the last 30 days and fields for its cost,
# packing and postage, ordered by units so the products that matter most come first. Nothing
# in the contract gave that list: `top_missing` stops at ten and the stock list carries no
# cost. This operation was added to the contract on 29 September 2026 with S20. Units are
# counted exactly as coverage counts them, and the cost is the one in force today, with the
# same tie-break as the product figures.

class SkuCost(BaseModel):
    sku_id: UUID
    seller_sku: str | None = None
    tiktok_sku_id: str | None = None
    product_title: str | None = None
    variant_label: str | None = None
    units_30d: int = Field(ge=0)
    cost: Money | None = None
    packing: Money | None = None
    postage: Money | None = None


class SkuCostList(BaseModel):
    skus: list[SkuCost]


SKU_COSTS_SQL = """
with sold as (
  select ol.sku_id, sum(ol.quantity) as units
    from order_lines ol join orders o on o.id = ol.order_id
   where ol.shop_id = %(shop)s and o.cancelled_at is null
     and (o.order_created_at at time zone 'Europe/London')::date between %(from)s and %(to)s
   group by ol.sku_id
),
cost as (
  select distinct on (sku_id) sku_id, cost_minor, packing_minor, postage_minor
    from product_costs where shop_id = %(shop)s and effective_from <= %(to)s
   order by sku_id, effective_from desc, created_at desc
)
select k.id, k.seller_sku, k.tiktok_sku_id, p.title, k.variant_label,
       coalesce(s.units, 0) as units, c.cost_minor, c.packing_minor, c.postage_minor,
       (select trim(currency) from shops where id = %(shop)s) as currency
  from skus k
  left join products p on p.id = k.product_id
  left join sold s on s.sku_id = k.id
  left join cost c on c.sku_id = k.id
 where k.shop_id = %(shop)s
 order by coalesce(s.units, 0) desc, p.title nulls last, k.variant_label nulls last, k.id
"""


@router.get("/shops/{shopId}/costs", response_model=SkuCostList, summary="Every variant with its cost")
def list_sku_costs(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
) -> SkuCostList:
    from datetime import timedelta

    today = business_today()
    with tenant(account.id) as conn:
        rows = conn.execute(SKU_COSTS_SQL, {"shop": str(shop_id), "from": today - timedelta(days=29),
                                            "to": today}).fetchall()

    def m(v, cur):
        return money(int(v), cur or "GBP") if v is not None else None

    return SkuCostList(skus=[
        SkuCost(sku_id=r[0], seller_sku=r[1], tiktok_sku_id=r[2], product_title=r[3], variant_label=r[4],
                units_30d=int(r[5]), cost=m(r[6], r[9]), packing=m(r[7], r[9]), postage=m(r[8], r[9]))
        for r in rows
    ])
