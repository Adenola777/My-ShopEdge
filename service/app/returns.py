"""Returns. `listReturns` and `getReturnMetrics`, tracing RET-1 and RET-6.

`checkReturnItem` is served since 28 September 2026, on the four rules the owner accepted
that day (A30.2). It is at the end of this file.

LISTING

Each return carries its money from `return_reconciliation`, which is `security_invoker`, so
row level security holds through it. `refund` is TikTok's refund as stored. `return_cost`
is the return costs of A4.2 posted against the return: return postage and write-offs,
returned as the positive amount lost, which is how A4 writes the formula. Null when
nothing was posted, so an unchecked return does not read as costing nothing.

`awaiting_check_count` counts items awaiting a check across the shop, the same count Today
uses for "returns to check", so the two screens cannot disagree.

METRICS, RET-6

- Returned units are return item quantities, dated by when the refund completed and
  otherwise when it was requested, in Europe/London. This is the same rule the product
  ranking uses, so the rate and the Products screen count the same units.
- Units sold are the units behind gross sales in the period, the ranking's own count.
- Return costs and write-offs are A4.2's formula, −(return_cost + write_off entries),
  dated by `basis_day`.

**Derived, not ruled.** The contract bounds `return_rate` to 0 to 1, and more units can come
back in a month than were sold in it, because a return follows its sale. The rate is
therefore capped at 1, and `returns_units` beside it shows the true count. With nothing
sold the rate is 0.

Both queries were run on the development branch, 24 September 2026.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import Account, require_account
from .dates import business_today, now_utc
from .db import tenant
from .idempotency import record, replay, request_hash
from .money import Money, money
from .problems import Problem
from .settlements import MAX_LIMIT, decode_cursor, encode_cursor
from .shops import require_shop

router = APIRouter(tags=["Returns"])

LONDON_DAY = "((coalesce(r.refund_completed_at, r.requested_at)) at time zone 'Europe/London')::date"


class ListedItem(BaseModel):
    """A return item as S8 needs it: its id to check, and which product it is."""
    id: UUID
    return_id: UUID
    sku_id: UUID | None = None
    quantity: int = Field(ge=1)
    seller_check_status: Literal["pending", "resellable", "unsellable", "not_applicable"]
    checked_at: datetime | None = None
    return_postage: Money | None = None
    product_title: str | None = None
    variant_label: str | None = None


class ReturnSummary(BaseModel):
    id: UUID
    tiktok_return_id: str
    tiktok_order_id: str
    tiktok_credit_note_number: str | None = None
    kind: Literal["cancellation", "refund_only", "return_refund"]
    status: str
    reason_code: str | None = None
    refund: Money | None = None
    requested_at: datetime | None = None
    refund_completed_at: datetime | None = None
    items_awaiting_check: int = Field(default=0, ge=0)
    return_cost: Money | None = None
    items: list[ListedItem] = []


class ReturnPage(BaseModel):
    returns: list[ReturnSummary]
    awaiting_check_count: int = Field(ge=0)
    next_cursor: str | None = None


LIST_SQL = """
select r.id, r.tiktok_return_id, rr.tiktok_order_id, r.tiktok_credit_note_number, r.kind,
       r.status, r.reason_code, r.refund_minor, r.requested_at, r.refund_completed_at,
       rr.items_awaiting_check, rr.return_cost_minor, rr.write_off_minor,
       (select count(*) from ledger_entries le where le.return_id = r.id
         and le.entry_type in ('return_cost', 'write_off')) as cost_entries,
       coalesce(r.requested_at, r.created_at) as sort_at,
       (select trim(currency) from shops where id = r.shop_id) as currency
  from returns r
  join return_reconciliation rr on rr.return_id = r.id
 where {where}
 order by coalesce(r.requested_at, r.created_at) desc, r.id desc
 limit %s
"""


@router.get("/shops/{shopId}/returns", response_model=ReturnPage)
def list_returns(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    kind: Annotated[Literal["cancellation", "refund_only", "return_refund"] | None, Query()] = None,
    awaiting_check: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 50,
    cursor: Annotated[str | None, Query()] = None,
) -> ReturnPage:
    where = ["r.shop_id = %s"]
    args: list[Any] = [str(shop_id)]
    if kind:
        where.append("r.kind = %s")
        args.append(kind)
    if awaiting_check is not None:
        where.append("rr.items_awaiting_check " + ("> 0" if awaiting_check else "= 0"))
    if cursor:
        c_time, c_id = decode_cursor(cursor)
        where.append("(coalesce(r.requested_at, r.created_at), r.id) < (%s::timestamptz, %s::uuid)")
        args += [c_time, c_id]
    args.append(limit + 1)

    with tenant(account.id) as conn:
        cur = conn.execute(LIST_SQL.format(where=" and ".join(where)), args)
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
        waiting = conn.execute(
            "select count(*) from return_items where shop_id = %s "
            "and seller_check_status = 'pending'",
            (str(shop_id),),
        ).fetchone()
        # The page's items in one query, so S8 can check each by its id.
        ids = [str(r["id"]) for r in rows[:limit]]
        item_rows = conn.execute(
            "select ri.id, ri.return_id, ri.sku_id, ri.quantity, ri.seller_check_status, "
            "ri.checked_at, ri.return_postage_minor, p.title, k.variant_label "
            "from return_items ri left join skus k on k.id = ri.sku_id "
            "left join products p on p.id = k.product_id "
            "where ri.return_id = any(%s::uuid[]) order by ri.created_at, ri.id",
            (ids,),
        ).fetchall() if ids else []
    by_return: dict[str, list] = {}
    for it in item_rows:
        by_return.setdefault(str(it[1]), []).append(it)

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = encode_cursor(rows[-1]["sort_at"], rows[-1]["id"])

    out = []
    for r in rows:
        cur_code = r["currency"] or "GBP"
        lost = -int(r["return_cost_minor"] or 0) - int(r["write_off_minor"] or 0)
        out.append(ReturnSummary(
            id=r["id"], tiktok_return_id=r["tiktok_return_id"],
            tiktok_order_id=r["tiktok_order_id"],
            tiktok_credit_note_number=r["tiktok_credit_note_number"], kind=r["kind"],
            status=r["status"], reason_code=r["reason_code"],
            refund=money(int(r["refund_minor"]), cur_code) if r["refund_minor"] is not None else None,
            requested_at=r["requested_at"], refund_completed_at=r["refund_completed_at"],
            items_awaiting_check=int(r["items_awaiting_check"] or 0),
            return_cost=money(lost, cur_code) if int(r["cost_entries"]) > 0 else None,
            items=[
                ListedItem(
                    id=it[0], return_id=it[1], sku_id=it[2], quantity=it[3],
                    seller_check_status=it[4], checked_at=it[5],
                    return_postage=money(int(it[6]), cur_code) if it[6] is not None else None,
                    product_title=it[7], variant_label=it[8],
                )
                for it in by_return.get(str(r["id"]), [])
            ],
        ))
    return ReturnPage(returns=out, awaiting_check_count=int(waiting[0]) if waiting else 0,
                      next_cursor=next_cursor)


class MostReturned(BaseModel):
    product_id: UUID
    title: str | None = None
    units: int = Field(ge=0)
    cost: Money


class ReturnMetrics(BaseModel):
    period: dict[str, str]
    return_rate: float = Field(ge=0, le=1)
    returns_units: int = Field(ge=0)
    total_return_cost: Money
    write_off_total: Money
    most_returned: list[MostReturned]


METRICS_SQL = f"""
with returned as (
  select s.product_id, sum(ri.quantity) as units
    from return_items ri
    join returns r on r.id = ri.return_id
    join skus s on s.id = ri.sku_id
   where ri.shop_id = %(shop)s
     and {LONDON_DAY} between %(from)s and %(to)s
   group by s.product_id
),
sold as (
  select coalesce(sum(ol.quantity), 0) as units
    from (select distinct order_line_id from ledger_entries
           where shop_id = %(shop)s and category = 'gross_sales'
             and order_line_id is not null
             and basis_day between %(from)s and %(to)s) g
    join order_lines ol on ol.id = g.order_line_id
),
costs as (
  select s.product_id,
         -coalesce(sum(le.amount_minor) filter (where le.entry_type in ('return_cost','write_off')), 0) as lost,
         -coalesce(sum(le.amount_minor) filter (where le.entry_type = 'write_off'), 0) as written_off
    from ledger_entries le
    left join skus s on s.id = le.sku_id
   where le.shop_id = %(shop)s
     and le.entry_type in ('return_cost', 'write_off')
     and le.basis_day between %(from)s and %(to)s
   group by s.product_id
)
select 'product' as row_kind, p.id as product_id, p.title, rt.units, coalesce(c.lost, 0) as lost,
       null::bigint as sold_units, null::numeric as written_off
  from returned rt
  join products p on p.id = rt.product_id
  left join costs c on c.product_id = rt.product_id
union all
select 'totals', null, null,
       (select coalesce(sum(units), 0) from returned),
       (select coalesce(sum(lost), 0) from costs),
       (select units from sold),
       (select coalesce(sum(written_off), 0) from costs)
"""


@router.get("/shops/{shopId}/returns/metrics", response_model=ReturnMetrics)
def get_return_metrics(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    period_from: Annotated[date | None, Query(alias="from")] = None,
    period_to: Annotated[date | None, Query(alias="to")] = None,
) -> ReturnMetrics:
    today = business_today()
    start = period_from or today.replace(day=1)
    end = period_to or today
    if start > end:
        raise Problem(422, "validation_failed", "The period ends before it starts. Choose an end date on or after the start date.")

    with tenant(account.id) as conn:
        cur = conn.execute(METRICS_SQL, {"shop": str(shop_id), "from": start, "to": end})
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
        currency = conn.execute(
            "select trim(currency) from shops where id = %s", (str(shop_id),)
        ).fetchone()[0]

    totals = next(r for r in rows if r["row_kind"] == "totals")
    products = sorted((r for r in rows if r["row_kind"] == "product"),
                      key=lambda r: (-int(r["units"]), -int(r["lost"]), str(r["product_id"])))
    returned, sold = int(totals["units"]), int(totals["sold_units"] or 0)
    rate = 0.0 if sold == 0 else min(1.0, returned / sold)

    return ReturnMetrics(
        period={"from": start.isoformat(), "to": end.isoformat(), "basis": "sales"},
        return_rate=rate,
        returns_units=returned,
        total_return_cost=money(int(totals["lost"]), currency),
        write_off_total=money(int(totals["written_off"]), currency),
        most_returned=[
            MostReturned(product_id=r["product_id"], title=r["title"], units=int(r["units"]),
                         cost=money(int(r["lost"]), currency))
            for r in products[:5]
        ],
    )


# --- checkReturnItem, RET-3 and RET-4 ------------------------------------------------------
#
# The seller says whether a returned item came back usable. What each answer writes, from
# the contract, A4 and the owner's four rulings of 28 September 2026 (A30.2):
#
#   resellable      one stock movement of type return_resellable, and the units added to
#                   the seller's adjustment, because TikTok does not move stock on a return
#                   (A4, STK-8). No write-off.
#   unsellable      a write-off at the cost in force when the unit sold, and no stock
#                   movement, as the contract states. The units are counted in written_off.
#   not_applicable  nothing came back: no movement, no write-off, and no postage (A4.3).
#
# For all three, the checked units come off coming_back (A30.2 rule 4), never below zero.
# Return postage, where given, is a return_cost entry. Every entry attaches to the order
# line of the returned variant (rule 1) and carries the date of the check (rule 3). A check
# is one way, so a second one answers 409.
#
# **Refused rather than guessed.** A write-off needs a cost. Where the variant had no cost
# in force when it sold, the check is refused with a reason, because a zero write-off would
# understate what the seller lost. Where the order holds no line for the returned variant,
# the check is refused too, because rule 1 has nothing to attach to.


class CheckIn(BaseModel):
    seller_check_status: Literal["resellable", "unsellable", "not_applicable"]
    return_postage: Money | None = None


class ReturnItemOut(BaseModel):
    id: UUID
    return_id: UUID
    sku_id: UUID | None = None
    quantity: int = Field(ge=1)
    seller_check_status: Literal["pending", "resellable", "unsellable", "not_applicable"]
    checked_at: datetime | None = None
    return_postage: Money | None = None


class CheckOut(BaseModel):
    item: ReturnItemOut
    stock_movements_created: int = Field(ge=0, le=1)
    write_off: Money | None = None


@router.post("/shops/{shopId}/return-items/{returnItemId}/check", response_model=CheckOut)
def check_return_item(
    body: CheckIn,
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    item_id: Annotated[UUID, Path(alias="returnItemId")],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    status = body.seller_check_status
    postage = body.return_postage
    if postage is not None and postage.amount_minor < 0:
        raise Problem(422, "validation_failed", "Return postage cannot be negative.")
    if status == "not_applicable" and postage is not None and postage.amount_minor > 0:
        raise Problem(422, "validation_failed", "Nothing came back, so no return postage was paid.")

    op = "checkReturnItem"
    digest = request_hash(str(shop_id), str(item_id), status,
                          postage.amount_minor if postage else None)
    with tenant(account.id) as conn:
        again = replay(conn, account.id, op, idempotency_key, digest)
        if again:
            return JSONResponse(status_code=again[0], content=again[1])

        row = conn.execute(
            "select ri.id, ri.return_id, ri.sku_id, ri.quantity, ri.seller_check_status, "
            "r.order_id, trim(s.currency) "
            "from return_items ri join returns r on r.id = ri.return_id "
            "join shops s on s.id = ri.shop_id "
            "where ri.id = %s and ri.shop_id = %s for update of ri",
            (str(item_id), str(shop_id)),
        ).fetchone()
        if row is None:
            # The same answer for another account's item, for the reason in shops.py.
            raise Problem(404, "return_item_not_found", "That returned item was not found.")
        _, return_id, sku_id, quantity, current, order_id, currency = row
        currency = currency or "GBP"
        if current != "pending":
            raise Problem(409, "already_checked", "This item has already been checked. Checking is one way.")
        if postage is not None and postage.currency != currency:
            raise Problem(422, "validation_failed",
                          f"The postage is in {postage.currency} and this shop sells in {currency}. "
                          f"Enter it in {currency}.")

        writes_ledger = status == "unsellable" or (postage is not None and postage.amount_minor > 0)
        line = None
        if writes_ledger:
            line = conn.execute(
                "select ol.id, (o.order_created_at at time zone 'Europe/London')::date "
                "from order_lines ol join orders o on o.id = ol.order_id "
                "where ol.order_id = %s and ol.sku_id = %s order by ol.id limit 1",
                (str(order_id), str(sku_id) if sku_id else None),
            ).fetchone()
            if line is None:
                raise Problem(422, "no_order_line",
                              "This variant is not on the original order, so the return cannot be "
                              "recorded against it.")

        write_off_minor = None
        if status == "unsellable":
            cost = conn.execute(
                "select cost_minor from product_costs where shop_id = %s and sku_id = %s "
                "and effective_from <= %s order by effective_from desc, created_at desc limit 1",
                (str(shop_id), str(sku_id), line[1]),
            ).fetchone()
            if cost is None:
                raise Problem(422, "no_cost",
                              "This variant had no cost price on the day it sold, so the write-off cannot be worked "
                              "out. Add its cost price on the product page, dated on or before the day it "
                              "sold, then check the item again.")
            write_off_minor = int(cost[0]) * int(quantity)

        now = now_utc()
        month = business_today(now).replace(day=1)
        ref = f"return_item:{item_id}"

        def post(entry_type: str, category: str, amount: int) -> None:
            conn.execute(
                "insert into ledger_entries (shop_id, order_id, return_id, order_line_id, sku_id, "
                "entry_type, category, amount_minor, currency, occurred_at, basis_month, source, "
                "source_ref, attribution) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "'seller', %s, 'direct')",
                (str(shop_id), str(order_id), str(return_id), str(line[0]), str(sku_id),
                 entry_type, category, -amount, currency, now, month, ref),
            )

        if write_off_minor:
            post("write_off", "stock_written_off", write_off_minor)
        if postage is not None and postage.amount_minor > 0:
            post("return_cost", "return_shipping", postage.amount_minor)

        movements = 0
        if status == "resellable" and sku_id is not None:
            conn.execute(
                "insert into stock_movements (shop_id, sku_id, movement_type, quantity, "
                "return_id, return_item_id, created_by) values (%s, %s, 'return_resellable', %s, %s, %s, %s)",
                (str(shop_id), str(sku_id), int(quantity), str(return_id), str(item_id), str(account.id)),
            )
            movements = 1
        if sku_id is not None:
            conn.execute(
                "update stock_positions set "
                "coming_back = greatest(coming_back - %(q)s, 0), "
                "adjusted_delta = adjusted_delta + case when %(st)s = 'resellable' then %(q)s else 0 end, "
                "written_off = written_off + case when %(st)s = 'unsellable' then %(q)s else 0 end "
                "where shop_id = %(shop)s and sku_id = %(sku)s",
                {"q": int(quantity), "st": status, "shop": str(shop_id), "sku": str(sku_id)},
            )

        updated = conn.execute(
            "update return_items set seller_check_status = %s, checked_at = %s, checked_by = %s, "
            "return_postage_minor = %s where id = %s "
            "returning id, return_id, sku_id, quantity, seller_check_status, checked_at, return_postage_minor",
            (status, now, str(account.id), postage.amount_minor if postage else None, str(item_id)),
        ).fetchone()
        out = CheckOut(
            item=ReturnItemOut(
                id=updated[0], return_id=updated[1], sku_id=updated[2], quantity=updated[3],
                seller_check_status=updated[4], checked_at=updated[5],
                return_postage=money(int(updated[6]), currency) if updated[6] is not None else None,
            ),
            stock_movements_created=movements,
            write_off=money(write_off_minor, currency) if write_off_minor else None,
        )
        record(conn, account.id, op, idempotency_key, digest, 200, out.model_dump(mode="json"))
    return out
