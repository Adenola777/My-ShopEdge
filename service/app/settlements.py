"""Settlements. What TikTok said, what it held back, and what reached the bank.

Three figures on this screen are not the same number, and A18.3 is explicit about why
that matters:

    net proceeds    sales less every deduction
    reserve         money TikTok is holding, released later
    payout          what actually arrives

A seller who reads net proceeds as the amount landing in their account will believe TikTok
short-paid them by the reserved amount. All three are returned, always, even when the
reserve is zero, so the front end never has to decide whether to show a field.

The reserve is stored negative, because it is a deduction from the ledger's point of view.
It is returned exactly as stored. Presenting it as "£10.00 held" rather than "-£10.00" is
the screen's job, and doing it here would mean the API returning a sign that contradicts
the ledger.

Verified against the seeded seller on the development branch, 23 September 2026. Statement
202608A-0002: net proceeds 14750, reserve 1000 withheld, payout 13750. All three
settlements reconcile with nothing unexplained, and the four components sum exactly to the
statement amount on each.
"""

from __future__ import annotations

import base64
import json
from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from .auth import Account, require_account
from .db import tenant
from .money import Money, money
from .problems import Problem
from .shops import require_shop

router = APIRouter(tags=["Settlements"])

MAX_LIMIT = 100


def encode_cursor(statement_time: datetime, settlement_id: UUID) -> str:
    raw = json.dumps({"t": statement_time.isoformat(), "i": str(settlement_id)})
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[str, str]:
    """Opaque to the caller, and refused rather than guessed at if it is malformed.

    A cursor that cannot be decoded is a client error, not a reason to silently return the
    first page. Silently restarting a pagination loop is how a caller ends up reading the
    same page forever.
    """
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        return data["t"], data["i"]
    except Exception as exc:
        raise Problem(400, "invalid_cursor", "That page cursor is not valid.") from exc


class Settlement(BaseModel):
    id: UUID
    tiktok_statement_id: str
    tiktok_payment_id: str | None = None
    settlement_reference: str | None = None
    statement_time: datetime
    activity_date: date
    paid_at: datetime | None = None
    payment_status: str
    statement_amount: Money
    total_reserve: Money
    payable_amount: Money
    tiktok_invoice_number: str | None = None


class SettlementPage(BaseModel):
    settlements: list[Settlement]
    next_cursor: str | None = None


class SettlementComponents(BaseModel):
    net_sales: Money
    fees: Money
    shipping_cost: Money
    adjustments: Money
    difference: Money
    region_mapping_conflict: bool = False


class SettlementReconciliation(BaseModel):
    orders_settled: int
    net_proceeds: Money
    invoiced_gross: Money | None = None
    unexplained: Money


class SettledOrder(BaseModel):
    order_id: UUID
    tiktok_order_id: str
    settled: Money | None = None


class SettlementInvoice(BaseModel):
    invoice_number: str
    invoice_type: str
    issued_on: date
    period_start: date | None = None
    period_end: date | None = None
    net: Money
    vat: Money
    gross: Money


class SettlementDetail(BaseModel):
    settlement: Settlement
    components: SettlementComponents
    reconciliation: SettlementReconciliation
    invoice: SettlementInvoice | None = None
    orders: list[SettledOrder]


def _settlement(row: dict[str, Any]) -> Settlement:
    cur = row["currency"]
    return Settlement(
        id=row["id"],
        tiktok_statement_id=row["tiktok_statement_id"],
        tiktok_payment_id=row["tiktok_payment_id"],
        settlement_reference=row["settlement_reference"],
        statement_time=row["statement_time"],
        activity_date=row["activity_date"],
        paid_at=row["paid_at"],
        payment_status=row["payment_status"],
        statement_amount=money(row["statement_amount_minor"], cur),
        total_reserve=money(row["total_reserve_amount_minor"] or 0, cur),
        payable_amount=money(
            row["payable_amount_minor"]
            if row["payable_amount_minor"] is not None
            else row["statement_amount_minor"],
            cur,
        ),
        tiktok_invoice_number=row["tiktok_invoice_number"],
    )


SETTLEMENT_COLUMNS = """
  id, tiktok_statement_id, tiktok_payment_id, settlement_reference,
  statement_time, activity_date, paid_at, payment_status, currency,
  statement_amount_minor, payable_amount_minor, total_reserve_amount_minor,
  tiktok_invoice_number
"""


@router.get("/shops/{shopId}/settlements", response_model=SettlementPage)
def list_settlements(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    period_from: Annotated[date | None, Query(alias="from")] = None,
    period_to: Annotated[date | None, Query(alias="to")] = None,
    payment_status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 50,
    cursor: Annotated[str | None, Query()] = None,
) -> SettlementPage:
    where = ["shop_id = %s"]
    args: list[Any] = [str(shop_id)]

    if period_from:
        where.append("activity_date >= %s")
        args.append(period_from)
    if period_to:
        where.append("activity_date <= %s")
        args.append(period_to)
    if payment_status:
        where.append("payment_status = %s")
        args.append(payment_status)
    if cursor:
        # Keyset rather than offset. An offset shifts under a caller when a new statement
        # arrives mid-pagination, which on a finance screen means a settlement silently
        # skipped rather than a row appearing twice.
        c_time, c_id = decode_cursor(cursor)
        where.append("(statement_time, id) < (%s::timestamptz, %s::uuid)")
        args += [c_time, c_id]

    args.append(limit + 1)
    sql = (
        f"select {SETTLEMENT_COLUMNS} from settlements where {' and '.join(where)} "
        "order by statement_time desc, id desc limit %s"
    )

    with tenant(account.id) as conn:
        cur = conn.execute(sql, args)
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(last["statement_time"], last["id"])

    return SettlementPage(
        settlements=[_settlement(r) for r in rows], next_cursor=next_cursor
    )


@router.get(
    "/shops/{shopId}/settlements/{settlementId}", response_model=SettlementDetail
)
def get_settlement(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    settlementId: UUID,
) -> SettlementDetail:
    with tenant(account.id) as conn:
        cur = conn.execute(
            f"select {SETTLEMENT_COLUMNS}, net_sales_minor, fee_minor, "
            "shipping_cost_minor, adjustment_minor "
            "from settlements where id = %s and shop_id = %s",
            (str(settlementId), str(shop_id)),
        )
        cols = [d.name for d in cur.description]
        row = cur.fetchone()
        if row is None:
            # Same answer as a settlement on another account, for the reason in shops.py.
            raise Problem(404, "settlement_not_found", "That settlement was not found.")
        s = dict(zip(cols, row, strict=True))

        rec = conn.execute(
            "select orders_settled, net_proceeds_minor, invoiced_gross_minor, "
            "unexplained_minor from settlement_reconciliation where settlement_id = %s",
            (str(settlementId),),
        ).fetchone()

        inv = conn.execute(
            "select tiktok_invoice_number, invoice_type, issued_on, period_start, period_end, "
            "net_minor, vat_minor, gross_minor, currency from tiktok_invoices "
            "where settlement_id = %s and shop_id = %s order by created_at desc limit 1",
            (str(settlementId), str(shop_id)),
        ).fetchone()

        orders = conn.execute(
            "select o.id, o.tiktok_order_id, "
            "       sum(le.amount_minor) filter (where le.entry_type = 'sale') as settled "
            "  from ledger_entries le "
            "  join orders o on o.id = le.order_id "
            " where le.settlement_id = %s "
            " group by o.id, o.tiktok_order_id "
            # min() because order_created_at is not in the GROUP BY and Postgres will not
            # accept it bare. Caught by running the query rather than by reading it.
            " order by min(o.order_created_at)",
            (str(settlementId),),
        ).fetchall()

    currency = s["currency"]
    net_sales = s["net_sales_minor"] or 0
    fees = s["fee_minor"] or 0
    shipping = s["shipping_cost_minor"] or 0
    adjustments = s["adjustment_minor"] or 0

    components = SettlementComponents(
        net_sales=money(net_sales, currency),
        fees=money(fees, currency),
        shipping_cost=money(shipping, currency),
        adjustments=money(adjustments, currency),
        # What TikTok's own four components fail to explain about its own total. Zero on
        # every seeded statement. A non-zero value here is TikTok disagreeing with itself,
        # which is worth surfacing rather than absorbing.
        difference=money(
            s["statement_amount_minor"] - (net_sales + fees + shipping + adjustments),
            currency,
        ),
    )

    reconciliation = SettlementReconciliation(
        orders_settled=int(rec[0]) if rec else 0,
        net_proceeds=money(int(rec[1]) if rec else 0, currency),
        invoiced_gross=money(int(rec[2]), currency) if rec and rec[2] is not None else None,
        unexplained=money(int(rec[3]) if rec else 0, currency),
    )

    invoice = None
    if inv is not None:
        icur = inv[8]
        invoice = SettlementInvoice(
            invoice_number=inv[0], invoice_type=inv[1], issued_on=inv[2],
            period_start=inv[3], period_end=inv[4], net=money(int(inv[5]), icur),
            vat=money(int(inv[6]), icur), gross=money(int(inv[7]), icur),
        )

    return SettlementDetail(
        settlement=_settlement(s),
        components=components,
        reconciliation=reconciliation,
        invoice=invoice,
        orders=[
            SettledOrder(
                order_id=o[0],
                tiktok_order_id=o[1],
                settled=money(int(o[2]), currency) if o[2] is not None else None,
            )
            for o in orders
        ],
    )


# --- recordSettlementInvoice ---------------------------------------------------------------
#
# The first version was written by Emergent AI in `Adenola777/MYSHOPEDGE` (commit 3f1bd43,
# 27 September 2026) and brought into this repository on 28 September at the owner's
# instruction. It stored the number and discarded the amounts.
#
# No TikTok API returns a seller's fee invoice. On 7 October 2026 every path in TikTok's own
# specification (`@tts-open-toolkit/cli` 0.1.7) was searched for "invoice": the only invoice
# endpoints are Brazil's NF-e upload and its webhook (A9.8). The owner ruled the same day that
# the seller types the invoice in from Seller Center, and that the PDF is uploaded once the
# store for it is settled (A10). This records the typed invoice in `tiktok_invoices`, whose
# check constraint refuses a gross that is not net plus VAT, and links it to the statement so
# `settlement_reconciliation.invoiced_gross_minor` carries it.


class SettlementInvoiceIn(BaseModel):
    invoice_number: str
    invoice_type: str | None = Field(default=None, max_length=120)
    issued_on: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    gross: Money | None = None
    net: Money | None = None
    vat: Money | None = None


def _checked_invoice(body: SettlementInvoiceIn, currency: str) -> dict[str, Any] | None:
    """The invoice to store, or None when only the number was sent. Refuses a partial one."""
    parts = (body.gross, body.net, body.vat, body.issued_on, body.invoice_type)
    if not any(p is not None for p in parts):
        return None
    if any(p is None for p in parts) or not (body.invoice_type or "").strip():
        raise Problem(422, "validation_failed",
                      "To record the invoice, enter its type, date, net, VAT and gross.")
    if {body.gross.currency, body.net.currency, body.vat.currency} != {currency}:
        raise Problem(422, "validation_failed",
                      f"The invoice amounts must be in {currency}, the statement's currency.")
    if body.gross.amount_minor != body.net.amount_minor + body.vat.amount_minor:
        raise Problem(422, "validation_failed",
                      "The gross must equal the net plus the VAT. Check the figures against "
                      "the invoice.")
    if body.period_start and body.period_end and body.period_start > body.period_end:
        raise Problem(422, "validation_failed", "The period cannot end before it starts.")
    return {
        "invoice_type": body.invoice_type.strip(), "issued_on": body.issued_on,
        "period_start": body.period_start, "period_end": body.period_end,
        "net": body.net.amount_minor, "vat": body.vat.amount_minor,
        "gross": body.gross.amount_minor,
    }


@router.put("/shops/{shopId}/settlements/{settlementId}/invoice", response_model=Settlement,
            summary="Record the TikTok fee invoice number")
def record_settlement_invoice(
    body: SettlementInvoiceIn,
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    settlementId: UUID,
) -> Settlement:
    number = body.invoice_number.strip()
    if not number:
        raise Problem(422, "validation_failed", "An invoice number is required.")
    if len(number) > 64:
        raise Problem(422, "validation_failed", "That invoice number is too long.")

    with tenant(account.id) as conn:
        cur = conn.execute(
            f"update settlements set tiktok_invoice_number = %s where id = %s and shop_id = %s "
            f"returning {SETTLEMENT_COLUMNS}",
            (number, str(settlementId), str(shop_id)),
        )
        cols = [d.name for d in cur.description]
        row = cur.fetchone()
        if row is None:
            # Same answer as a settlement on another account, for the reason in shops.py.
            raise Problem(404, "settlement_not_found", "That settlement was not found.")
        out = dict(zip(cols, row, strict=True))
        invoice = _checked_invoice(body, out["currency"])
        if invoice is not None:
            # A statement carries one invoice. Another number recorded on it earlier is
            # unlinked, so the reconciliation does not count two.
            conn.execute(
                "update tiktok_invoices set settlement_id = null "
                "where settlement_id = %s and shop_id = %s and tiktok_invoice_number <> %s",
                (str(settlementId), str(shop_id), number),
            )
            conn.execute(
                "insert into tiktok_invoices (shop_id, tiktok_invoice_number, invoice_type, "
                "issued_on, period_start, period_end, net_minor, vat_minor, gross_minor, "
                "currency, settlement_id, source_ref) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'seller_entered') "
                "on conflict (shop_id, tiktok_invoice_number) do update set "
                "invoice_type = excluded.invoice_type, issued_on = excluded.issued_on, "
                "period_start = excluded.period_start, period_end = excluded.period_end, "
                "net_minor = excluded.net_minor, vat_minor = excluded.vat_minor, "
                "gross_minor = excluded.gross_minor, currency = excluded.currency, "
                "settlement_id = excluded.settlement_id",
                (str(shop_id), number, invoice["invoice_type"], invoice["issued_on"],
                 invoice["period_start"], invoice["period_end"], invoice["net"],
                 invoice["vat"], invoice["gross"], out["currency"], str(settlementId)),
            )
    return _settlement(out)
