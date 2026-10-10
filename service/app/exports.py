"""Exports: `createExport`, `getExport`, `listExports`, `requestAccountExport`,
`getAccountExport` and `listAccountExports`.

Built 29 September 2026. The file store is decided (A10.8 as amended, `storage.py`), and this
module is the worker that A10.8 and CLAUDE.md said both operations were waiting for.

WHERE THE WORK RUNS

Each request answers 202 and the file is built after the answer, in the same process,
through FastAPI's background tasks. The service is one long-lived process on Render (A28),
so there is no separate worker to deploy. A build that a restart interrupts would leave its
job queued for ever, so a read of a job still queued five minutes after it was requested
builds it there and then. A job is therefore never stranded, and never built twice at once
by the same request.

WHAT THE SHOP FILES HOLD (MON-2, A3 S23, A18.6)

- `month_summary`: the Money screen's calculator for the period, section by section, from
  `money_view.calculate`. Its totals therefore equal the screen's, which is MON-2's acceptance.
- `ledger`: every ledger entry in the period on the chosen basis, with its TikTok identifiers.
- `transactions`: one row per order line, A2's grid across every product, with the money in
  each column taken from the same ledger entries. It carries no cost column, because a cost
  belongs to a variant and a period rather than to one line.

Every file opens with the shop name, the period, the basis and the time it was built, which
A3 S23 requires. A3 also asks for the logo, which a CSV cannot carry, and the seller's own
layout, which no document describes, so neither is attempted. A file lives seven days (A3 S23).

WHAT THE ACCOUNT ARCHIVE HOLDS (ACC-4)

A zip with one JSON file and one CSV file for every table that holds the account's rows,
read through `tenant()`, so row level security decides what is included. The stored TikTok
tokens are left out, because they are secrets, and so is the idempotency cache, which is
replayed answers kept for 24 hours. The archive lives seven days, the same as a shop file.

THE TWO LISTS (8 October 2026)

`listExports` and `listAccountExports` return the twenty most recent jobs, newest first, so a
seller who leaves the screen can come back to a file. A list carries no signed link, because
a link lives fifteen minutes and a list can sit open longer; the screen asks the single read
for a fresh one. A list only reads: a job past its seven days reads `expired` without being
written, and a job stranded in `queued` is built by the single read, as before.

**Unverified against AWS.** Like `storage.py`, this has run against a local stand-in for S3.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import storage
from .auth import Account, require_account
from .dates import business_today, now_utc
from .db import tenant
from .idempotency import record, replay, request_hash
from .money_view import TIKTOK_FEES, calculate
from .problems import Problem
from .shops import require_shop

log = logging.getLogger(__name__)
router = APIRouter()

LIFE = timedelta(days=7)
STALE = timedelta(minutes=5)
MAX_SPAN_DAYS = 24 * 31  # history is twenty four months on every plan

Kind = Literal["month_summary", "ledger", "transactions"]
Fmt = Literal["xlsx", "csv"]


class ExportList(BaseModel):
    exports: list[ExportJob]


class ExportIn(BaseModel):
    kind: Kind
    format: Fmt
    basis: Literal["sales", "cash"]
    period_start: date
    period_end: date


class ExportJob(BaseModel):
    id: UUID
    status: Literal["queued", "ready", "failed", "expired"]
    requested_at: datetime
    ready_at: datetime | None = None
    expires_at: datetime | None = None
    download_url: str | None = None
    size_bytes: int | None = None


LIST_LIMIT = 20


def _shown_status(status: str, expires_at: datetime | None) -> str:
    """What a list reports, without writing: a ready file past its seven days is expired."""
    if status == "ready" and expires_at is not None and expires_at <= now_utc():
        return "expired"
    return status


class ShopExportJob(ExportJob):
    kind: Kind
    format: Fmt
    basis: Literal["sales", "cash"]
    period_start: date
    period_end: date
    row_count: int | None = None


# --- building a table ----------------------------------------------------------------------

def _pounds(minor: int | None) -> str:
    return "" if minor is None else f"{Decimal(minor) / 100:.2f}"


def _header(shop_name: str, start: date, end: date, basis: str, built: datetime) -> list[list[str]]:
    return [
        ["Shop", shop_name],
        ["Period", f"{start.isoformat()} to {end.isoformat()}"],
        ["Basis", "Sales basis (by sale date)" if basis == "sales" else "Cash basis (by settlement)"],
        ["Built", built.isoformat(timespec="seconds")],
        ["Amounts", "Pounds sterling. A deduction is negative."],
        [],
    ]


# The same sentences the Money screen shows (web/src/lib/terms.js, keptReason), so a file
# handed to an accountant never carries a code. Added 8 October 2026.
KEPT_REASONS = {
    "incomplete_costs": "Not known, because not every product sold in the period has a cost price.",
    "no_sales": "Nothing sold in this period.",
}

# The confidence code in words, by the rules in money_view.calculate.
CONFIDENCE_WORDS = {
    "confirmed": "Confirmed",
    "estimated": "Estimated, because TikTok has not yet settled some amounts in the period.",
    "incomplete": "Incomplete, because not every product sold in the period has a cost price.",
}


def _month_summary(conn, shop_id: UUID, start: date, end: date, basis: str) -> list[list[Any]]:
    view = calculate(conn, shop_id, start, end, basis)
    rows: list[list[Any]] = [["Section", "Line", "TikTok field", "Amount (£)"]]
    for s in view.sections:
        for line in s.lines:
            rows.append([s.label, line.label, line.tiktok_fee_type or "", _pounds(line.amount.amount_minor)])
        rows.append([s.label, s.subtotal_label or "Subtotal", "", _pounds(s.subtotal.amount_minor)])
    t = view.totals
    rows += [
        [],
        ["Totals", "Gross sales", "", _pounds(t.gross_sales.amount_minor)],
        ["Totals", "Net sales", "", _pounds(t.net_sales.amount_minor)],
        ["Totals", "Net proceeds", "", _pounds(t.net_proceeds.amount_minor)],
        ["Totals", "Gross profit after returns", "", _pounds(view.kept.amount_minor) if view.kept else
         KEPT_REASONS.get(view.kept_reason or "", "Not known.")],
        ["Totals", "Gross margin after returns", "",
         f"{Decimal(str(t.gross_margin_after_returns)) * 100:.2f}%" if t.gross_margin_after_returns is not None
         else KEPT_REASONS.get(view.kept_reason or "", "Not known.")],
        ["Totals", "Confidence", "", CONFIDENCE_WORDS.get(view.confidence, view.confidence)],
    ]
    return rows


LEDGER_SQL = """
select le.basis_day, le.settlement_month, le.occurred_at, le.entry_type, le.category,
       le.tiktok_fee_type, le.amount_minor, le.currency, o.tiktok_order_id, ol.tiktok_line_id,
       st.tiktok_statement_id, k.seller_sku, k.tiktok_sku_id, p.title, le.attribution, le.source,
       le.source_ref, le.id
  from ledger_entries le
  left join orders o on o.id = le.order_id
  left join order_lines ol on ol.id = le.order_line_id
  left join settlements st on st.id = le.settlement_id
  left join skus k on k.id = le.sku_id
  left join products p on p.id = k.product_id
 where le.shop_id = %(shop)s and {date_column} >= %(from)s and {date_column} <= %(to)s
 order by le.basis_day, le.occurred_at, le.id
"""


def _ledger(conn, shop_id: UUID, start: date, end: date, basis: str) -> list[list[Any]]:
    column = "le.basis_day" if basis == "sales" else "le.settlement_month"
    cur = conn.execute(LEDGER_SQL.format(date_column=column),
                       {"shop": str(shop_id), "from": start, "to": end})
    rows: list[list[Any]] = [[
        "Sale date", "Settlement month", "Occurred at", "Entry type", "Category", "TikTok field",
        "Amount (£)", "Currency", "TikTok order ID", "TikTok line ID", "TikTok statement ID",
        "Seller SKU", "TikTok SKU ID", "Product", "Attribution", "Source", "Source reference",
        "Entry ID",
    ]]
    total = 0
    for r in cur.fetchall():
        total += int(r[6])
        rows.append([
            r[0].isoformat() if r[0] else "", r[1].isoformat() if r[1] else "",
            r[2].isoformat() if r[2] else "", r[3], r[4] or "", r[5] or "", _pounds(int(r[6])),
            (r[7] or "").strip(), r[8] or "", r[9] or "", r[10] or "", r[11] or "", r[12] or "",
            r[13] or "", r[14] or "", r[15] or "", r[16] or "", str(r[17]),
        ])
    rows.append(["Total", "", "", "", "", "", _pounds(total)])
    return rows


TRANSACTIONS_SQL = """
select o.tiktok_order_id, ol.tiktok_line_id, p.title, k.seller_sku, ol.quantity,
       min(le.basis_day) as sale_date,
       coalesce(sum(le.amount_minor) filter (where le.category = 'gross_sales'), 0) as gross,
       coalesce(sum(le.amount_minor) filter (where le.category = 'seller_discount'), 0) as discount,
       coalesce(sum(le.amount_minor) filter (where le.category = any(%(fees)s)), 0) as fees,
       coalesce(sum(le.amount_minor) filter (where le.category = 'refund'), 0) as refund,
       coalesce(sum(le.amount_minor) filter (where le.category in ('return_shipping', 'stock_written_off')), 0) as returns
  from ledger_entries le
  join order_lines ol on ol.id = le.order_line_id
  join orders o on o.id = ol.order_id
  left join skus k on k.id = ol.sku_id
  left join products p on p.id = k.product_id
 where le.shop_id = %(shop)s and {date_column} >= %(from)s and {date_column} <= %(to)s
   and le.category is distinct from 'cost_of_goods_sold'
 group by o.tiktok_order_id, ol.tiktok_line_id, p.title, k.seller_sku, ol.quantity
 order by sale_date, o.tiktok_order_id, ol.tiktok_line_id
"""


def _transactions(conn, shop_id: UUID, start: date, end: date, basis: str) -> list[list[Any]]:
    column = "le.basis_day" if basis == "sales" else "le.settlement_month"
    cur = conn.execute(TRANSACTIONS_SQL.format(date_column=column),
                       {"shop": str(shop_id), "from": start, "to": end, "fees": list(TIKTOK_FEES)})
    rows: list[list[Any]] = [[
        "TikTok order ID", "TikTok line ID", "Product", "Seller SKU", "Units", "Sale date",
        "Gross sales (£)", "Your discounts (£)", "TikTok fees (£)", "Refunds (£)",
        "Net proceeds (£)", "Return costs (£)",
    ]]
    sums = [0, 0, 0, 0, 0, 0]
    for r in cur.fetchall():
        gross, discount, fees, refund, returns = (int(x) for x in r[6:11])
        net = gross + discount + fees + refund
        for i, v in enumerate((gross, discount, fees, refund, net, returns)):
            sums[i] += v
        rows.append([r[0] or "", r[1] or "", r[2] or "", r[3] or "", r[4], r[5].isoformat() if r[5] else "",
                     *(_pounds(v) for v in (gross, discount, fees, refund, net, returns))])
    rows.append(["Total", "", "", "", "", "", *(_pounds(v) for v in sums)])
    return rows


BUILDERS = {"month_summary": _month_summary, "ledger": _ledger, "transactions": _transactions}


def render(fmt: str, header: list[list[Any]], table: list[list[Any]]) -> tuple[bytes, str]:
    """The file's bytes and its content type."""
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerows(header + table)
        # A byte order mark, so Excel opens the pound sign correctly.
        return ("﻿" + buf.getvalue()).encode("utf-8"), "text/csv"
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Export"
    for row in header + table:
        ws.append(row)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# --- shop exports ---------------------------------------------------------------------------

JOB_COLS = ("id, status, created_at, ready_at, expires_at, size_bytes, kind, format, basis, "
            "period_start, period_end, row_count, storage_key, failure_reason, shop_id")


def _job(row, url: str | None = None) -> ShopExportJob:
    (id_, status, created, ready, expires, size, kind, fmt, basis, start, end, count, _key,
     _fail, _shop) = row
    return ShopExportJob(id=id_, status=status, requested_at=created, ready_at=ready,
                         expires_at=expires, download_url=url, size_bytes=size, kind=kind,
                         format=fmt, basis=basis, period_start=start, period_end=end,
                         row_count=count)


def build_in(conn, export_id: UUID) -> bool:
    """Builds one queued export on a connection the caller has scoped, and stores it.

    Returns whether it built the file. A job that is missing or no longer queued is left
    alone. Any fault raises, and the caller's transaction decides what survives. Split out of
    `build_shop_export` on 9 October 2026 so the scheduled exports (`export_schedules.py`)
    build their files here rather than through a second builder.
    """
    row = conn.execute(f"select {JOB_COLS} from exports where id = %s for update",
                       (str(export_id),)).fetchone()
    if row is None or row[1] != "queued":
        return False
    kind, fmt, basis, start, end, shop_id = row[6], row[7], row[8], row[9], row[10], row[14]
    name = conn.execute("select coalesce(shop_name, tiktok_shop_id) from shops where id = %s",
                        (str(shop_id),)).fetchone()[0]
    built = now_utc()
    table = BUILDERS[kind](conn, shop_id, start, end, basis)
    data, content_type = render(fmt, _header(name, start, end, basis, built), table)
    key = f"exports/{shop_id}/{export_id}/{storage.nonce()}.{fmt}"
    storage.put_bytes(key, data, content_type)
    conn.execute(
        "update exports set status = 'ready', storage_key = %s, ready_at = %s, "
        "expires_at = %s, size_bytes = %s, row_count = %s where id = %s",
        (key, built, built + LIFE, len(data), max(len(table) - 2, 0), str(export_id)),
    )
    return True


def build_shop_export(account_id: UUID, export_id: UUID) -> None:
    """Builds one queued export and stores it. Safe to call twice: a finished job is left alone."""
    try:
        with tenant(account_id) as conn:
            build_in(conn, export_id)
    except Exception:  # noqa: BLE001
        log.exception("export %s failed", export_id)
        reason = ("We could not prepare this download because of a fault at our end. Your "
                  "records are unaffected. Request it again later, or email "
                  "info@inspirecraftglobal.com.")
        with tenant(account_id) as conn:
            conn.execute("update exports set status = 'failed', failure_reason = %s "
                         "where id = %s and status = 'queued'", (reason, str(export_id)))


class ShopExportList(BaseModel):
    exports: list[ShopExportJob]


@router.get("/shops/{shopId}/exports", response_model=ShopExportList, tags=["Exports"],
            summary="The shop's recent exports")
def list_exports(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
) -> ShopExportList:
    with tenant(account.id) as conn:
        rows = conn.execute(f"select {JOB_COLS} from exports where shop_id = %s "
                            "order by created_at desc, id desc limit %s",
                            (str(shop_id), LIST_LIMIT)).fetchall()
    jobs = []
    for row in rows:
        job = _job(row)
        job.status = _shown_status(job.status, job.expires_at)
        jobs.append(job)
    return ShopExportList(exports=jobs)


@router.post("/shops/{shopId}/exports", status_code=202, response_model=ShopExportJob,
             tags=["Exports"], summary="Request an export")
def create_export(
    body: ExportIn,
    background: BackgroundTasks,
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    if body.period_end < body.period_start:
        raise Problem(422, "validation_failed", "The period ends before it starts. Choose an end date on or after the start date.")
    if (body.period_end - body.period_start).days > MAX_SPAN_DAYS:
        raise Problem(422, "validation_failed", "An export covers at most twenty four months.")
    if body.period_start > business_today():
        raise Problem(422, "validation_failed", "The period has not started yet.")
    op = "createExport"
    digest = request_hash(str(shop_id), body.model_dump(mode="json"))
    with tenant(account.id) as conn:
        again = replay(conn, account.id, op, idempotency_key, digest)
        if again:
            return JSONResponse(status_code=again[0], content=again[1])
        row = conn.execute(
            "insert into exports (shop_id, kind, format, basis, period_start, period_end) "
            f"values (%s, %s, %s, %s, %s, %s) returning {JOB_COLS}",
            (str(shop_id), body.kind, body.format, body.basis, body.period_start, body.period_end),
        ).fetchone()
        out = _job(row)
        record(conn, account.id, op, idempotency_key, digest, 202, out.model_dump(mode="json"))
    background.add_task(build_shop_export, account.id, out.id)
    return JSONResponse(status_code=202, content=out.model_dump(mode="json"))


@router.get("/shops/{shopId}/exports/{exportId}", response_model=ShopExportJob,
            tags=["Exports"], summary="Export status and signed download URL")
def get_export(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    export_id: Annotated[UUID, Path(alias="exportId")],
) -> ShopExportJob:
    def read():
        with tenant(account.id) as conn:
            return conn.execute(f"select {JOB_COLS} from exports where id = %s and shop_id = %s",
                                (str(export_id), str(shop_id))).fetchone()

    row = read()
    if row is None:
        raise Problem(404, "export_not_found", "That export was not found.")
    if row[1] == "queued" and now_utc() - row[2] > STALE:
        build_shop_export(account.id, export_id)
        row = read()
    if row[1] == "ready" and row[4] is not None and row[4] <= now_utc():
        with tenant(account.id) as conn:
            conn.execute("update exports set status = 'expired' where id = %s", (str(export_id),))
        row = read()
    url = None
    if row[1] == "ready" and row[12]:
        ext = row[7]
        url, _ = storage.presign_get(row[12], f"myshopedge-{row[6]}-{row[9]}-to-{row[10]}.{ext}")
    return _job(row, url)


# --- the account archive ----------------------------------------------------------------------

# Every table that holds the account's rows under row level security, read through tenant().
ACCOUNT_TABLES = (
    "accounts", "tax_profiles", "subscriptions", "shops", "alert_settings", "products", "skus",
    "product_costs", "product_events", "cost_uploads", "orders", "order_lines", "order_settlements",
    "settlements", "ledger_entries", "returns", "return_items", "stock_positions", "stock_movements",
    "discrepancies", "notifications", "other_channel_sales", "daily_metrics", "sync_runs",
    "exports", "export_schedules", "account_exports", "tiktok_invoices", "change_log", "audit_log",
    "raw_events",
)
# The connection's metadata, never its tokens.
TIKTOK_CONNECTION_COLUMNS = ("shop_id, scopes, required_scopes, authorised_at, revoked_at, "
                             "access_expires_at, refresh_expires_at, refresh_attempted_at, "
                             "refresh_succeeded_at, refresh_failure_code, refresh_failure_reason")


def _plain(v: Any) -> Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (UUID, Decimal)):
        return str(v)
    if isinstance(v, (bytes, memoryview)):
        return None
    return v


def build_account_archive(conn) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        sources = [(t, f"select * from {t}") for t in ACCOUNT_TABLES]
        sources.append(("tiktok_connections", f"select {TIKTOK_CONNECTION_COLUMNS} from tiktok_connections"))
        for name, sql in sources:
            cur = conn.execute(sql)
            cols = [d.name for d in cur.description]
            rows = [[_plain(v) for v in r] for r in cur.fetchall()]
            z.writestr(f"json/{name}.json", json.dumps([dict(zip(cols, r, strict=True)) for r in rows], indent=1))
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(cols)
            w.writerows([[json.dumps(v) if isinstance(v, (dict, list)) else v for v in r] for r in rows])
            z.writestr(f"csv/{name}.csv", buf.getvalue())
        z.writestr("README.txt",
                   "Everything MyShopEdge holds about your account, one file per table, in JSON and "
                   "CSV. Amounts are in pence. The stored TikTok tokens are not included, because "
                   "they are secrets.\n")
    return out.getvalue()


ACCOUNT_COLS = "id, status, requested_at, ready_at, expires_at, size_bytes, storage_key"


def _account_job(row, url: str | None = None) -> ExportJob:
    return ExportJob(id=row[0], status=row[1], requested_at=row[2], ready_at=row[3],
                     expires_at=row[4], size_bytes=row[5], download_url=url)


def build_account_export(account_id: UUID, export_id: UUID) -> None:
    try:
        with tenant(account_id) as conn:
            row = conn.execute("select status from account_exports where id = %s for update",
                               (str(export_id),)).fetchone()
            if row is None or row[0] != "queued":
                return
            data = build_account_archive(conn)
            key = f"account-exports/{account_id}/{export_id}/{storage.nonce()}.zip"
            storage.put_bytes(key, data, "application/zip")
            built = now_utc()
            conn.execute("update account_exports set status = 'ready', storage_key = %s, "
                         "ready_at = %s, expires_at = %s, size_bytes = %s where id = %s",
                         (key, built, built + LIFE, len(data), str(export_id)))
    except Exception:  # noqa: BLE001
        log.exception("account export %s failed", export_id)
        reason = ("We could not prepare this download because of a fault at our end. Your "
                  "records are unaffected. Request it again later, or email "
                  "info@inspirecraftglobal.com.")
        with tenant(account_id) as conn:
            conn.execute("update account_exports set status = 'failed', failure_reason = %s "
                         "where id = %s and status = 'queued'", (reason, str(export_id)))


@router.get("/me/export", response_model=ExportList, tags=["Account"],
            summary="The account's recent data downloads")
def list_account_exports(account: Annotated[Account, Depends(require_account)]) -> ExportList:
    with tenant(account.id) as conn:
        rows = conn.execute(f"select {ACCOUNT_COLS} from account_exports where account_id = %s "
                            "order by requested_at desc, id desc limit %s",
                            (str(account.id), LIST_LIMIT)).fetchall()
    jobs = []
    for row in rows:
        job = _account_job(row)
        job.status = _shown_status(job.status, job.expires_at)
        jobs.append(job)
    return ExportList(exports=jobs)


@router.post("/me/export", status_code=202, response_model=ExportJob, tags=["Account"],
             summary="Request a download of the account's data")
def request_account_export(
    background: BackgroundTasks,
    account: Annotated[Account, Depends(require_account)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    op = "requestAccountExport"
    digest = request_hash(str(account.id))
    with tenant(account.id) as conn:
        again = replay(conn, account.id, op, idempotency_key, digest)
        if again:
            return JSONResponse(status_code=again[0], content=again[1])
        busy = conn.execute(
            "select id from account_exports where account_id = %s and status = 'queued' "
            "and requested_at > now() - interval '5 minutes'", (str(account.id),),
        ).fetchone()
        if busy:
            raise Problem(409, "export_in_progress",
                          "A download of your data is already being prepared.")
        row = conn.execute(f"insert into account_exports (account_id) values (%s) returning {ACCOUNT_COLS}",
                           (str(account.id),)).fetchone()
        out = _account_job(row)
        record(conn, account.id, op, idempotency_key, digest, 202, out.model_dump(mode="json"))
    background.add_task(build_account_export, account.id, out.id)
    return JSONResponse(status_code=202, content=out.model_dump(mode="json"))


@router.get("/me/export/{exportId}", response_model=ExportJob, tags=["Account"],
            summary="A data download's status and signed link")
def get_account_export(
    account: Annotated[Account, Depends(require_account)],
    export_id: Annotated[UUID, Path(alias="exportId")],
) -> ExportJob:
    def read():
        with tenant(account.id) as conn:
            return conn.execute(f"select {ACCOUNT_COLS} from account_exports where id = %s",
                                (str(export_id),)).fetchone()

    row = read()
    if row is None:
        raise Problem(404, "export_not_found", "That download was not found.")
    if row[1] == "queued" and now_utc() - row[2] > STALE:
        build_account_export(account.id, export_id)
        row = read()
    if row[1] == "ready" and row[4] is not None and row[4] <= now_utc():
        with tenant(account.id) as conn:
            conn.execute("update account_exports set status = 'expired' where id = %s", (str(export_id),))
        row = read()
    url = None
    if row[1] == "ready" and row[6]:
        url, _ = storage.presign_get(row[6], "myshopedge-your-data.zip")
    return _account_job(row, url)
