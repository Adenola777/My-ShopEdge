"""Twelve-month bars, `getTrends` (DSH-7). Built 29 September 2026.

Each bar is one London calendar month, and its figure is `money_view.calculate` for that
month, the same arithmetic the Money screen runs. So a bar and the Money screen for the same
month cannot disagree, and the twelve bars sum to the twelve-month figure, which is the QA
acceptance (DSH-7: "Bars sum to the rolling 12-month figure").

**`units` is a count, not money.** The contract typed every point as Money, which cannot
carry a unit count honestly. On 29 September the contract was amended: a point carries
`value` for a money measure and `count` for `units`, and `value` may be null where the
figure is not known for that month, which is `kept` when a product sold that month has no
cost. A bar is never drawn from a guess.

**A bar is complete** when its month has ended, falls on or after the first month the ledger
holds for the shop, and, on the sales basis, holds no sale, refund or TikTok deduction still waiting
for a settlement. The contract asks for exactly this: "False for a month still settling, or
one before the shop connected."
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from .auth import Account, require_account
from .dates import business_today
from .db import tenant
from .entitlements import features_for, refuse
from .money import Money
from .money_view import SETTLED_BY_TIKTOK, calculate
from .products import NET_PROCEEDS_TYPES, RETURN_LOSS_TYPES
from .products import SQL as PRODUCTS_SQL
from .shops import require_shop

router = APIRouter(tags=["Money"])

Measure = Literal["gross_sales", "net_proceeds", "kept", "units"]


class TrendPoint(BaseModel):
    month: str
    value: Money | None = None
    count: int | None = None
    complete: bool


class Trends(BaseModel):
    measure: Measure
    basis: Literal["sales", "cash"]
    points: list[TrendPoint]


UNSETTLED_SQL = """
select count(*) from ledger_entries le
 where le.shop_id = %(shop)s and le.basis_day >= %(from)s and le.basis_day <= %(to)s
   and le.settlement_id is null and le.entry_type = any(%(settled)s)
"""


def _months(today: date) -> list[tuple[date, date]]:
    """The twelve London months ending with the current one, oldest first."""
    out = []
    y, m = today.year, today.month
    for _ in range(12):
        start = date(y, m, 1)
        nxt = date(y + (m == 12), m % 12 + 1, 1)
        out.append((start, date.fromordinal(nxt.toordinal() - 1)))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return list(reversed(out))


@router.get("/shops/{shopId}/trends", response_model=Trends, response_model_exclude_none=False,
            summary="Twelve-month bars")
def get_trends(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    basis: Annotated[Literal["sales", "cash"], Query()] = "sales",
    measure: Annotated[Measure, Query()] = "net_proceeds",
) -> Trends:
    plan = features_for(account.id)
    if basis == "cash" and "basis" not in plan:
        raise refuse("basis")
    if measure == "kept" and "profit" not in plan:
        raise refuse("profit")
    today = business_today()
    points: list[TrendPoint] = []
    with tenant(account.id) as conn:
        # The contract marks "one before the shop connected" as incomplete. The history TikTok
        # hands over at connection reaches back before the shop row was made, so measuring
        # from `shops.created_at` marked every month of it partial, which was seen on the
        # local copy on 29 September. What the rule is for is a month nothing was read for,
        # so the first month the ledger holds is where the shop's data begins.
        first = conn.execute(
            "select min(basis_day) from ledger_entries where shop_id = %s", (str(shop_id),),
        ).fetchone()[0]
        for start, end in _months(today):
            view = calculate(conn, shop_id, start, end, basis)
            if measure == "units":
                date_column = "le.basis_day" if basis == "sales" else "le.settlement_month"
                cur = conn.execute(PRODUCTS_SQL.format(date_column=date_column), {
                    "shop": str(shop_id), "from": start, "to": end,
                    "np": list(NET_PROCEEDS_TYPES), "rl": list(RETURN_LOSS_TYPES),
                })
                cols = [d.name for d in cur.description]
                units = sum(int(dict(zip(cols, r, strict=True))["units_sold"]) for r in cur.fetchall())
                point = TrendPoint(month=f"{start:%Y-%m}", count=units, complete=False)
            else:
                amount = {
                    "gross_sales": view.totals.gross_sales,
                    "net_proceeds": view.totals.net_proceeds,
                    # A month with no sales has no `kept` on the Money screen, which reads
                    # "no sales", but its return costs still happened, so the bar carries
                    # the gross profit after returns the calculator worked out for it.
                    "kept": view.kept if view.kept_reason != "no_sales"
                    else view.totals.gross_profit_after_returns,
                }[measure]
                point = TrendPoint(month=f"{start:%Y-%m}", value=amount, complete=False)

            settling = False
            if basis == "sales":
                settling = conn.execute(UNSETTLED_SQL, {
                    "shop": str(shop_id), "from": start, "to": end,
                    "settled": list(SETTLED_BY_TIKTOK),
                }).fetchone()[0] > 0
            point.complete = (end < today and first is not None
                              and start >= first.replace(day=1) and not settling)
            points.append(point)
    return Trends(measure=measure, basis=basis, points=points)
