"""Scheduled exports (MON-8, A5.7): `listExportSchedules`, `createExportSchedule`,
`updateExportSchedule`, `deleteExportSchedule`, and the daily runner.

Built 9 October 2026 with the owner's approval of that day. A5.7 sets the rule: the seller
chooses weekly on a weekday or monthly on a day from 1 to 28, a kind, a format and a basis,
and on that day the file is built without being asked for and the seller is told.

WHAT IS OFFERED

The kinds and formats are exactly those `exports.py` builds: `month_summary`, `ledger` and
`transactions`, each as Excel or CSV. The file is built by `exports.build_in`, the same code
`createExport` uses, so a scheduled file and a requested one for the same dates are the same
file. Each run is an ordinary row in `exports`, so it appears in the screen's recent files and
lives seven days like any other.

A weekly schedule is offered on the sales basis only. The ledger records the cash basis by
`settlement_month`, the first day of the month a payout settled (`tiktok_sync.london_month`),
and holds no settlement day. A Monday to Sunday week on the cash basis would therefore be
empty in most weeks and hold a whole month's payouts in the week containing the 1st. A5 names
`settlement_day` for the cash basis, and it was never built.

THE DAYS AND THE PERIOD EACH RUN COVERS

`day_of_week` runs from 1, Monday, to 7, Sunday, as ISO 8601 numbers them and as A5's weeks
begin. Days are London days (`dates.business_today`). A5 does not say which period a run
covers, so this module chose, and the choice is recorded here and in the contract:

- a monthly run covers the previous calendar month, the last month that is complete;
- a weekly run covers the previous Monday to Sunday week, the last week that is complete.

A run on the 28th therefore covers the month before, not the 28 days of the month so far.

THE RUNNER

`run_due` is called by `scripts/sync_shops.py` after the sync, so no new cron job is needed.
It lists every active schedule through `export_schedules_due()` (migration 0030), then judges
and builds each one inside `tenant()`. One schedule's run is one transaction: the export row,
the file, `last_run_at` and the notice are written together or not at all. A schedule already
run on today's London date is left alone, so running the job twice in a day builds nothing
the second time. When file storage is not configured (`storage_unconfigured`), the
transaction rolls back, so the schedule is not marked as run and no notice is sent, and the
result says so. A file whose upload succeeded before a later step failed is left in the store
without a row, under the shop's `exports/` prefix.

**Email.** A5.7 says the seller is told in the app and, if they have not opted out, by email.
Since 10 October 2026 `notice_email` emails the `scheduled_export_ready` notice through Resend,
once migration 0031 is applied.

**Plans.** A18.6 and the price sheet sell scheduled exports on Pro. No code gates any feature
by plan and the owner has not ruled which features to gate, so this is not gated.

**Unverified against R2**, like `storage.py`: the runner has built files against a local
stand-in for S3 only (`testdata/scheduled_exports_check.py`).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import Account, require_account
from .dates import business_today, now_utc
from .db import tenant, unscoped
from .exports import Fmt, Kind, build_in
from .idempotency import record, replay, request_hash
from .problems import Problem
from .shops import require_shop

log = logging.getLogger(__name__)
router = APIRouter()

Basis = Literal["sales", "cash"]
Cadence = Literal["weekly", "monthly"]


class ScheduleIn(BaseModel):
    kind: Kind
    format: Fmt
    basis: Basis
    cadence: Cadence
    day_of_week: int | None = Field(default=None, ge=1, le=7)
    day_of_month: int | None = Field(default=None, ge=1, le=28)


class ScheduleChange(BaseModel):
    kind: Kind | None = None
    format: Fmt | None = None
    basis: Basis | None = None
    cadence: Cadence | None = None
    day_of_week: int | None = Field(default=None, ge=1, le=7)
    day_of_month: int | None = Field(default=None, ge=1, le=28)
    active: bool | None = None


class ExportSchedule(BaseModel):
    id: UUID
    kind: Kind
    format: Fmt
    basis: Basis
    cadence: Cadence
    day_of_week: int | None = None
    day_of_month: int | None = None
    active: bool
    last_run_at: datetime | None = None
    created_at: datetime


class ExportScheduleList(BaseModel):
    schedules: list[ExportSchedule]


COLS = ("id, kind, format, basis, cadence, day_of_week, day_of_month, active, last_run_at, "
        "created_at")


def _schedule(row) -> ExportSchedule:
    return ExportSchedule(**dict(zip(COLS.split(", "), row, strict=True)))


def _check(s: dict[str, Any]) -> None:
    """The rules a schedule must meet, in the words a seller reads."""
    if s["cadence"] == "weekly":
        if s["day_of_week"] is None:
            raise Problem(422, "validation_failed", "Choose the weekday the file is built on.")
        if s["day_of_month"] is not None:
            raise Problem(422, "validation_failed",
                          "A weekly schedule takes a weekday, not a day of the month.")
        if s["basis"] == "cash":
            raise Problem(422, "validation_failed",
                          "A weekly file can only be on the sales basis, because MyShopEdge "
                          "records the cash basis by the month a payout settled and not by its "
                          "day. Choose a monthly schedule for the cash basis.")
    else:
        if s["day_of_month"] is None:
            raise Problem(422, "validation_failed", "Choose the day of the month the file is built on.")
        if s["day_of_week"] is not None:
            raise Problem(422, "validation_failed",
                          "A monthly schedule takes a day of the month, not a weekday.")


NOT_FOUND = "That scheduled export was not found."


# --- the four operations ---------------------------------------------------------------------

@router.get("/shops/{shopId}/export-schedules", response_model=ExportScheduleList,
            tags=["Exports"], summary="The shop's scheduled exports")
def list_export_schedules(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
) -> ExportScheduleList:
    with tenant(account.id) as conn:
        rows = conn.execute(f"select {COLS} from export_schedules where shop_id = %s "
                            "order by created_at, id", (str(shop_id),)).fetchall()
    return ExportScheduleList(schedules=[_schedule(r) for r in rows])


@router.post("/shops/{shopId}/export-schedules", status_code=201, response_model=ExportSchedule,
             tags=["Exports"], summary="Schedule an export")
def create_export_schedule(
    body: ScheduleIn,
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    _check(body.model_dump())
    op = "createExportSchedule"
    digest = request_hash(str(shop_id), body.model_dump(mode="json"))
    with tenant(account.id) as conn:
        again = replay(conn, account.id, op, idempotency_key, digest)
        if again:
            return JSONResponse(status_code=again[0], content=again[1])
        row = conn.execute(
            "insert into export_schedules (shop_id, kind, format, basis, cadence, day_of_week, "
            f"day_of_month) values (%s, %s, %s, %s, %s, %s, %s) returning {COLS}",
            (str(shop_id), body.kind, body.format, body.basis, body.cadence, body.day_of_week,
             body.day_of_month),
        ).fetchone()
        out = _schedule(row).model_dump(mode="json")
        record(conn, account.id, op, idempotency_key, digest, 201, out)
    return JSONResponse(status_code=201, content=out)


@router.patch("/shops/{shopId}/export-schedules/{scheduleId}", response_model=ExportSchedule,
              tags=["Exports"], summary="Pause, resume or change a scheduled export")
def update_export_schedule(
    body: ScheduleChange,
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    schedule_id: Annotated[UUID, Path(alias="scheduleId")],
) -> ExportSchedule:
    change = body.model_dump(exclude_unset=True)
    if not change:
        raise Problem(422, "validation_failed", "Nothing was changed, because no change was sent.")
    if "active" in change and change["active"] is None:
        raise Problem(422, "validation_failed", "Active must be true or false.")
    with tenant(account.id) as conn:
        row = conn.execute(f"select {COLS} from export_schedules where id = %s and shop_id = %s "
                           "for update", (str(schedule_id), str(shop_id))).fetchone()
        if row is None:
            raise Problem(404, "schedule_not_found", NOT_FOUND)
        merged = _schedule(row).model_dump()
        merged.update(change)
        # A change of cadence drops the day that belongs to the other cadence, unless the
        # request named it, in which case `_check` refuses the pair.
        if merged["cadence"] == "weekly" and "day_of_month" not in change:
            merged["day_of_month"] = None
        if merged["cadence"] == "monthly" and "day_of_week" not in change:
            merged["day_of_week"] = None
        for field in ("kind", "format", "basis", "cadence"):
            if merged[field] is None:
                raise Problem(422, "validation_failed", f"{field.capitalize()} cannot be empty.")
        _check(merged)
        row = conn.execute(
            "update export_schedules set kind = %s, format = %s, basis = %s, cadence = %s, "
            "day_of_week = %s, day_of_month = %s, active = %s where id = %s "
            f"returning {COLS}",
            (merged["kind"], merged["format"], merged["basis"], merged["cadence"],
             merged["day_of_week"], merged["day_of_month"], merged["active"], str(schedule_id)),
        ).fetchone()
    return _schedule(row)


@router.delete("/shops/{shopId}/export-schedules/{scheduleId}", status_code=204,
               tags=["Exports"], summary="Remove a scheduled export")
def delete_export_schedule(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
    schedule_id: Annotated[UUID, Path(alias="scheduleId")],
) -> Response:
    with tenant(account.id) as conn:
        row = conn.execute("delete from export_schedules where id = %s and shop_id = %s "
                           "returning id", (str(schedule_id), str(shop_id))).fetchone()
    if row is None:
        raise Problem(404, "schedule_not_found", NOT_FOUND)
    return Response(status_code=204)


# --- the runner ------------------------------------------------------------------------------

def due_on(cadence: str, day_of_week: int | None, day_of_month: int | None, day: date) -> bool:
    """Whether a schedule falls due on a London date."""
    if cadence == "weekly":
        return day.isoweekday() == day_of_week
    return day.day == day_of_month


def period_for(cadence: str, day: date) -> tuple[date, date]:
    """The period a run on `day` covers: the last complete month, or the last complete week."""
    if cadence == "monthly":
        end = day.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end
    monday = day - timedelta(days=day.isoweekday() - 1)
    return monday - timedelta(days=7), monday - timedelta(days=1)


def long_date(d: date) -> str:
    return f"{d.day} {d.strftime('%B %Y')}"


KIND_WORDS = {"month_summary": "month summary", "ledger": "ledger",
              "transactions": "transactions file"}
BASIS_WORDS = {"sales": "sales basis", "cash": "cash basis"}


def _notify(conn, account_id, shop_id, schedule_id, export_id, kind: str, basis: str,
            start: date, end: date, today: date) -> None:
    """One in-app notice per run. The dedupe key names the schedule and the London date."""
    conn.execute(
        "insert into notifications (account_id, shop_id, type, severity, title, body, "
        "entity_type, entity_id, dedupe_key) values (%s, %s, 'scheduled_export_ready', 'info', "
        "%s, %s, 'export', %s, %s) on conflict (account_id, dedupe_key) do nothing",
        (str(account_id), str(shop_id),
         f"Your scheduled {KIND_WORDS[kind]} is ready.",
         f"It covers {long_date(start)} to {long_date(end)} on the {BASIS_WORDS[basis]}. "
         "You can download it from Export for seven days.",
         str(export_id), f"scheduled_export:{schedule_id}:{today.isoformat()}"))


def run_schedule(schedule_id, shop_id, account_id, now: datetime) -> dict[str, Any] | None:
    """Judges one schedule and builds its file if it is due. Never raises.

    Returns None when the schedule is not due today, and a result for the job's output
    otherwise: `built`, `already_run`, `storage_unconfigured` or `error`.
    """
    today = business_today(now)
    result: dict[str, Any] = {"schedule_id": str(schedule_id), "shop_id": str(shop_id)}
    try:
        with tenant(account_id) as conn:
            row = conn.execute(f"select {COLS} from export_schedules where id = %s "
                               "for update skip locked", (str(schedule_id),)).fetchone()
            if row is None:
                return None  # removed since it was listed, or another run holds it
            s = _schedule(row)
            if not s.active or not due_on(s.cadence, s.day_of_week, s.day_of_month, today):
                return None
            if s.last_run_at is not None and business_today(s.last_run_at) == today:
                result["status"] = "already_run"
                return result
            start, end = period_for(s.cadence, today)
            result["period"] = f"{start.isoformat()} to {end.isoformat()}"
            export_id = conn.execute(
                "insert into exports (shop_id, kind, format, basis, period_start, period_end) "
                "values (%s, %s, %s, %s, %s, %s) returning id",
                (str(shop_id), s.kind, s.format, s.basis, start, end)).fetchone()[0]
            build_in(conn, export_id)
            conn.execute("update export_schedules set last_run_at = %s where id = %s",
                         (now, str(schedule_id)))
            _notify(conn, account_id, shop_id, schedule_id, export_id, s.kind, s.basis,
                    start, end, today)
            result.update(status="built", export_id=str(export_id))
    except Problem as p:
        if p.code == "storage_unconfigured":
            result["status"] = "storage_unconfigured"
        else:
            result.update(status="error", error=f"{p.code}: {p.detail}")
    except Exception as err:  # noqa: BLE001  one schedule's fault must not stop the others
        log.exception("scheduled export %s failed", schedule_id)
        result.update(status="error", error=f"{type(err).__name__}: {err}")
    return result


def run_due(now: datetime | None = None) -> list[dict[str, Any]]:
    """Builds every scheduled export due on today's London date that has not run today.

    Raises only when the schedules cannot be listed, for example before migration 0030 is
    applied, in which case `psycopg.errors.UndefinedFunction` reaches the caller.
    """
    now = now or now_utc()
    with unscoped() as conn:
        listed = conn.execute(
            "select schedule_id, shop_id, account_id from export_schedules_due()").fetchall()
    results = (run_schedule(sid, shop, acc, now) for sid, shop, acc in listed)
    return [r for r in results if r is not None]
