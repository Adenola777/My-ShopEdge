"""The admin backend's service side (A34). Written 10 October 2026, on the owner's approval of
A34 the same day.

**Unverified against Neon and Stack.** Every route has run against a local PostgreSQL 16 built
from empty by `migrate.py` only (`testdata/admin_check.py`). Migration 0032, which the views
need, is applied to no Neon branch, and no real admin has signed in.

WHO GETS IN, `require_admin`

1. `ADMIN_EMAILS` on the service holds the allowed addresses, separated by commas. Unset or
   empty, every admin route answers 404.
2. The bearer token is verified exactly as a seller's is (`auth.verify`).
3. A reviewer token is refused (A34.3), because the reviewer path exists for TikTok's review of
   the demo service and must never reach an admin route.
4. The provider's own record, `neon_auth.users_sync`, must hold the subject with
   `raw_json.primary_email_verified` true and an email on the list. The record is used rather
   than the token's claims for the reason A34.3 gives.

Every refusal, whatever its cause, is the same 404 a path that does not exist gives, raised as
Starlette's own `HTTPException`, so the body and headers match byte for byte. The cause is
logged at info level for the operator.

HOW IT READS AND ACTS

The views read through the SECURITY DEFINER functions of migration 0032, which return no TikTok
token, no webhook payload and no money figure of a seller (A34.8, ruling 4). Each action runs
inside `tenant()` for the one account it acts on, under row level security, as the seller's
own request would, and writes one `audit_log` row in the same transaction, with the admin's
email as `actor`. Views are not logged (A34.5).

Every action is a POST with no body, so a refused request cannot be told apart from a missing
path by a body validation error answered before the admin check.
"""

from __future__ import annotations

import logging
import os
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Request
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import auth, billing, db, exports, notice_email
from .account_deletion import CancelOut, DeletionAcknowledgement, cancel_closing, close_account
from .plans import PLAN_ORDER, PLANS
from .problems import Problem

log = logging.getLogger("myshopedge.admin")
LONDON = ZoneInfo("Europe/London")
MAX_ROWS = 500


@dataclass(frozen=True)
class Admin:
    email: str
    subject: str


def _hidden(reason: str) -> StarletteHTTPException:
    log.info("admin route refused: %s", reason)
    return StarletteHTTPException(status_code=404, detail="Not Found")


def allowed_emails() -> set[str]:
    return {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}


def _identity(subject: str) -> tuple[str | None, bool] | None:
    with db.unscoped() as conn:
        row = conn.execute(
            "select email, coalesce((raw_json ->> 'primary_email_verified')::boolean, false) "
            "from neon_auth.users_sync where id = %s and deleted_at is null",
            (subject,),
        ).fetchone()
    return (row[0], bool(row[1])) if row else None


def require_admin(request: Request) -> Admin:
    allowed = allowed_emails()
    if not allowed:
        raise _hidden("ADMIN_EMAILS is not set")
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _hidden("no bearer token")
    try:
        claims = auth.verify(token)
    except Exception as err:  # noqa: BLE001  every failure is the same 404
        raise _hidden(f"token not verified ({type(err).__name__})") from err
    if claims.get("iss") == auth.REVIEWER_ISS:
        raise _hidden("reviewer token")
    identity = _identity(str(claims.get("sub")))
    if identity is None:
        raise _hidden("subject not in users_sync")
    email, verified = identity
    if not verified:
        raise _hidden("email not verified")
    if not email or email.lower() not in allowed:
        raise _hidden("email not on the allow-list")
    return Admin(email=email.lower(), subject=str(claims["sub"]))


router = APIRouter(prefix="/admin", tags=["Admin"])
AdminDep = Annotated[Admin, Depends(require_admin)]


def _rows(sql: str, args: tuple = ()) -> list[dict[str, Any]]:
    with db.unscoped() as conn:
        cur = conn.execute(sql, args)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def _audit(conn, account_id: UUID | str, admin: Admin, action: str, entity_type: str,
           entity_id: UUID | str | None) -> None:
    conn.execute(
        "insert into audit_log (account_id, actor, action, entity_type, entity_id) "
        "values (%s, %s, %s, %s, %s)",
        (str(account_id), f"admin:{admin.email}", action, entity_type,
         str(entity_id) if entity_id else None))


# --- the views ------------------------------------------------------------------------------

class AdminAccount(BaseModel):
    account_id: UUID
    email: str
    display_name: str | None = None
    status: Literal["active", "suspended", "deleted"]
    created_at: datetime
    deleted_at: datetime | None = None
    erased_at: datetime | None = None
    email_notices: bool
    plan_slug: str | None = None
    plan_status: str | None = None
    trial_end: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool | None = None
    shop_count: int


class AdminAccountList(BaseModel):
    accounts: list[AdminAccount]


@router.get("/accounts", response_model=AdminAccountList, summary="Every account")
def list_admin_accounts(
    admin: AdminDep,
    email: Annotated[str | None, Query(max_length=320)] = None,
) -> AdminAccountList:
    rows = _rows("select * from admin_accounts()")
    if email is not None:
        wanted = email.strip().lower()
        rows = [r for r in rows if r["email"].lower() == wanted]
    return AdminAccountList(accounts=[AdminAccount(**r) for r in rows])


class AdminShop(BaseModel):
    shop_id: UUID
    account_id: UUID
    account_email: str
    shop_name: str | None = None
    tiktok_shop_code: str | None = None
    region: str
    seller_type: str | None = None
    connection_status: str
    first_synced_at: datetime | None = None
    last_synced_at: datetime | None = None
    access_expires_at: datetime | None = None
    refresh_succeeded_at: datetime | None = None
    refresh_failure_code: str | None = None
    refresh_failure_reason: str | None = None
    revoked_at: datetime | None = None
    statements: int
    statements_unexplained: int


class AdminShopList(BaseModel):
    shops: list[AdminShop]


@router.get("/shops", response_model=AdminShopList, summary="Every shop and its connection")
def list_admin_shops(admin: AdminDep) -> AdminShopList:
    return AdminShopList(shops=[AdminShop(**r) for r in _rows("select * from admin_shops()")])


class AdminSyncRun(BaseModel):
    run_id: UUID
    shop_id: UUID
    shop_name: str | None = None
    kind: str
    domain: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    records_read: int | None = None
    records_written: int | None = None
    records_failed: int | None = None
    error: str | None = None


class AdminSyncRunList(BaseModel):
    runs: list[AdminSyncRun]


@router.get("/sync-runs", response_model=AdminSyncRunList, summary="The latest sync runs")
def list_admin_sync_runs(
    admin: AdminDep, limit: Annotated[int, Query(ge=1, le=MAX_ROWS)] = 100,
) -> AdminSyncRunList:
    return AdminSyncRunList(
        runs=[AdminSyncRun(**r) for r in _rows("select * from admin_sync_runs(%s)", (limit,))])


class AdminWebhookEvent(BaseModel):
    event_id: UUID
    received_at: datetime
    event_type: str | None = None
    tiktok_shop_id: str | None = None
    shop_id: UUID | None = None
    processed_at: datetime | None = None
    process_status: str | None = None
    process_note: str | None = None


class AdminWebhookEventList(BaseModel):
    events: list[AdminWebhookEvent]


@router.get("/webhook-events", response_model=AdminWebhookEventList,
            summary="The latest TikTok webhook events")
def list_admin_webhook_events(
    admin: AdminDep, limit: Annotated[int, Query(ge=1, le=MAX_ROWS)] = 100,
) -> AdminWebhookEventList:
    return AdminWebhookEventList(
        events=[AdminWebhookEvent(**r)
                for r in _rows("select * from admin_webhook_events(%s)", (limit,))])


class AdminEmailProblem(BaseModel):
    notification_id: UUID
    account_id: UUID
    account_email: str
    type: str
    created_at: datetime
    email_status: Literal["pending", "failed"]
    email_attempts: int
    email_note: str | None = None


class AdminNoticeEmails(BaseModel):
    counts: dict[str, int]
    problems: list[AdminEmailProblem]


@router.get("/notice-emails", response_model=AdminNoticeEmails,
            summary="Notice emails by state, and the ones not yet sent")
def get_admin_notice_emails(
    admin: AdminDep, limit: Annotated[int, Query(ge=1, le=MAX_ROWS)] = 100,
) -> AdminNoticeEmails:
    counts = {r["email_status"]: int(r["notices"])
              for r in _rows("select * from admin_email_counts()")}
    problems = [AdminEmailProblem(**r)
                for r in _rows("select * from admin_email_problems(%s)", (limit,))]
    return AdminNoticeEmails(counts=counts, problems=problems)


class AdminAuditEntry(BaseModel):
    audit_id: UUID
    occurred_at: datetime
    account_id: UUID | None = None
    actor: str
    action: str
    entity_type: str | None = None
    entity_id: UUID | None = None


class AdminAuditList(BaseModel):
    entries: list[AdminAuditEntry]


@router.get("/audit", response_model=AdminAuditList, summary="The latest audit log entries")
def list_admin_audit(
    admin: AdminDep, limit: Annotated[int, Query(ge=1, le=MAX_ROWS)] = 100,
) -> AdminAuditList:
    return AdminAuditList(
        entries=[AdminAuditEntry(**r) for r in _rows("select * from admin_audit(%s)", (limit,))])


class PlanFigure(BaseModel):
    plan_slug: str
    trialing: int
    paying: int
    past_due: int
    list_revenue_minor: int


class MonthCount(BaseModel):
    month: str
    signups: int


class AdminFigures(BaseModel):
    currency: str
    accounts: int
    accounts_active: int
    signups_by_month: list[MonthCount]
    plans: list[PlanFigure]
    list_revenue_minor: int
    note: str


@router.get("/figures", response_model=AdminFigures, summary="Sign-ups, trials and plans")
def get_admin_figures(admin: AdminDep) -> AdminFigures:
    """Read from `accounts` and `subscriptions`. Revenue is each paying plan's list price from
    `plans.py`, because Stripe is the record of money actually taken (A34.5). An account whose
    payment failed (`past_due`) is counted on its own and not as paying."""
    rows = _rows("select * from admin_accounts()")
    months = Counter(r["created_at"].astimezone(LONDON).strftime("%Y-%m") for r in rows)
    plans = []
    for slug in PLAN_ORDER:
        mine = [r for r in rows if r["plan_slug"] == slug]
        paying = sum(r["plan_status"] == "active" for r in mine)
        plans.append(PlanFigure(
            plan_slug=slug,
            trialing=sum(r["plan_status"] == "trialing" for r in mine),
            paying=paying,
            past_due=sum(r["plan_status"] == "past_due" for r in mine),
            list_revenue_minor=paying * PLANS[slug].price_minor,
        ))
    return AdminFigures(
        currency="GBP",
        accounts=len(rows),
        accounts_active=sum(r["status"] == "active" for r in rows),
        signups_by_month=[MonthCount(month=m, signups=n) for m, n in sorted(months.items())],
        plans=plans,
        list_revenue_minor=sum(p.list_revenue_minor for p in plans),
        note="Revenue is the list price of each paying plan each month, not money taken. "
             "Stripe holds the money actually taken.",
    )


# --- the actions ----------------------------------------------------------------------------

class AccountStatusOut(BaseModel):
    account_id: UUID
    status: Literal["active", "suspended"]
    renewal: str


SUSPENDED_TITLE = "Your MyShopEdge account is suspended."
SUSPENDED_BODY = ("MyShopEdge has suspended this account, so it cannot be used for now, and your "
                  "plan will not renew while it is suspended. Email info@inspirecraftglobal.com "
                  "and we will tell you why and what happens next.")
REACTIVATED_TITLE = "Your MyShopEdge account is active again."
REACTIVATED_BODY = ("You can sign in and use MyShopEdge as before. If the suspension stopped your "
                    "plan renewing, it renews again.")


def _notice(conn, account_id: UUID, type_: str, severity: str, title: str, body: str) -> None:
    conn.execute(
        "insert into notifications (account_id, type, severity, title, body, entity_type, "
        "entity_id, dedupe_key) values (%s, %s, %s, %s, %s, 'account', %s, %s)",
        (str(account_id), type_, severity, title, body, str(account_id),
         f"{type_}:{uuid.uuid4()}"))


def _locked_status(conn, account_id: UUID) -> str:
    row = conn.execute("select status from accounts where id = %s for update",
                       (str(account_id),)).fetchone()
    if row is None:
        raise Problem(404, "account_not_found", "That account was not found.")
    return row[0]


AccountPath = Annotated[UUID, Path(alias="accountId")]


@router.post("/accounts/{accountId}/suspend", response_model=AccountStatusOut,
             summary="Suspend an account")
def suspend_account(admin: AdminDep, background: BackgroundTasks,
                    account_id: AccountPath) -> AccountStatusOut:
    """A34.8 rulings 2 and 3: renewal stops through Stripe first, so a Stripe failure rolls the
    whole suspension back, and the seller is told by a notice and an email."""
    with db.tenant(account_id) as conn:
        status = _locked_status(conn, account_id)
        if status != "active":
            raise Problem(409, "not_active", f"This account is {status}, so it cannot be suspended.")
        renewal = billing.set_renewal_for_deletion(account_id, closing=True)
        conn.execute("update accounts set status = 'suspended' where id = %s", (str(account_id),))
        _notice(conn, account_id, "account_suspended", "critical", SUSPENDED_TITLE, SUSPENDED_BODY)
        _audit(conn, account_id, admin, "suspend_account", "account", account_id)
    background.add_task(notice_email.send_now, account_id)
    return AccountStatusOut(account_id=account_id, status="suspended", renewal=renewal)


@router.post("/accounts/{accountId}/reactivate", response_model=AccountStatusOut,
             summary="Reactivate a suspended account")
def reactivate_account(admin: AdminDep, background: BackgroundTasks,
                       account_id: AccountPath) -> AccountStatusOut:
    with db.tenant(account_id) as conn:
        status = _locked_status(conn, account_id)
        if status != "suspended":
            raise Problem(409, "not_suspended",
                          f"This account is {status}, so there is nothing to reactivate.")
        renewal = billing.set_renewal_for_deletion(account_id, closing=False)
        conn.execute("update accounts set status = 'active' where id = %s", (str(account_id),))
        _notice(conn, account_id, "account_reactivated", "info", REACTIVATED_TITLE,
                REACTIVATED_BODY)
        _audit(conn, account_id, admin, "reactivate_account", "account", account_id)
    background.add_task(notice_email.send_now, account_id)
    return AccountStatusOut(account_id=account_id, status="active", renewal=renewal)


class QueuedOut(BaseModel):
    queued: bool
    shop_id: UUID


def _sync_in_background(shop_id: UUID, account_id: UUID) -> None:
    from .tiktok_sync import run_one

    result = run_one(shop_id, account_id)
    log.info("admin sync of shop %s finished: %s", shop_id,
             "error" if "error" in result else "ok")


@router.post("/shops/{shopId}/sync", status_code=202, response_model=QueuedOut,
             summary="Sync one shop now")
def sync_shop_now(admin: AdminDep, background: BackgroundTasks,
                  shop_id: Annotated[UUID, Path(alias="shopId")]) -> QueuedOut:
    shop = next((r for r in _rows("select shop_id, account_id from admin_shops()")
                 if r["shop_id"] == shop_id), None)
    if shop is None:
        raise Problem(404, "shop_not_found", "That shop was not found.")
    with db.tenant(shop["account_id"]) as conn:
        _audit(conn, shop["account_id"], admin, "sync_shop", "shop", shop_id)
    background.add_task(_sync_in_background, shop_id, shop["account_id"])
    return QueuedOut(queued=True, shop_id=shop_id)


class RetryOut(BaseModel):
    notification_id: UUID
    email_status: Literal["pending"]


@router.post("/notifications/{notificationId}/retry-email", response_model=RetryOut,
             summary="Try a failed notice email again")
def retry_notice_email(admin: AdminDep, background: BackgroundTasks,
                       notification_id: Annotated[UUID, Path(alias="notificationId")]) -> RetryOut:
    found = next((r for r in _rows("select notification_id, account_id, email_status "
                                   "from admin_email_problems(%s)", (MAX_ROWS,))
                  if r["notification_id"] == notification_id), None)
    if found is None or found["email_status"] != "failed":
        raise Problem(409, "not_failed", "That notice's email has not failed, so there is "
                                         "nothing to try again.")
    with db.tenant(found["account_id"]) as conn:
        row = conn.execute(
            "update notifications set email_status = 'pending', email_attempts = 0, "
            "email_note = null where id = %s and email_status = 'failed' returning id",
            (str(notification_id),)).fetchone()
        if row is None:
            raise Problem(409, "not_failed", "That notice's email has not failed, so there is "
                                             "nothing to try again.")
        _audit(conn, found["account_id"], admin, "retry_notice_email", "notification",
               notification_id)
    background.add_task(notice_email.send_now, found["account_id"])
    return RetryOut(notification_id=notification_id, email_status="pending")


def _as_seller(account_id: UUID) -> auth.Account:
    """The seller's own export routes take an `Account`. Only the id is read by them."""
    with db.tenant(account_id) as conn:
        row = conn.execute("select email::text, status from accounts where id = %s",
                           (str(account_id),)).fetchone()
    if row is None:
        raise Problem(404, "account_not_found", "That account was not found.")
    return auth.Account(id=account_id, email=row[0], name=None, subject="admin", status=row[1])


@router.post("/accounts/{accountId}/export", status_code=202, response_model=exports.ExportJob,
             summary="Build an account's data export on its seller's request")
def request_export_for_account(admin: AdminDep, background: BackgroundTasks,
                               account_id: AccountPath):
    seller = _as_seller(account_id)
    answer = exports.request_account_export(background, seller, None)
    job = exports.ExportJob.model_validate_json(answer.body)
    with db.tenant(account_id) as conn:
        _audit(conn, account_id, admin, "build_account_export", "account_export", job.id)
    return answer


@router.get("/accounts/{accountId}/export/{exportId}", response_model=exports.ExportJob,
            summary="An account export's status and signed link")
def get_export_for_account(admin: AdminDep, account_id: AccountPath,
                           export_id: Annotated[UUID, Path(alias="exportId")]) -> exports.ExportJob:
    return exports.get_account_export(_as_seller(account_id), export_id)


@router.post("/accounts/{accountId}/deletion", status_code=202,
             response_model=DeletionAcknowledgement,
             summary="Close an account for deletion on its seller's request")
def delete_account(admin: AdminDep, account_id: AccountPath) -> DeletionAcknowledgement:
    """The same closing deleteMe does, with A30.1's thirty days. A suspended account is refused,
    as deleteMe refuses it, so it is reactivated first and its renewal handled once."""
    with db.tenant(account_id) as conn:
        row = conn.execute("select status, deleted_at from accounts where id = %s for update",
                           (str(account_id),)).fetchone()
        if row is None:
            raise Problem(404, "account_not_found", "That account was not found.")
        if row[0] == "suspended":
            raise Problem(409, "account_suspended",
                          "This account is suspended. Reactivate it before closing it.")
        out = close_account(conn, account_id, row[0], row[1])
        _audit(conn, account_id, admin, "delete_account", "account", account_id)
    return out


@router.post("/accounts/{accountId}/deletion/cancel", response_model=CancelOut,
             summary="Cancel an account's deletion on its seller's request")
def cancel_account_deletion(admin: AdminDep, account_id: AccountPath) -> CancelOut:
    with db.tenant(account_id) as conn:
        out = cancel_closing(conn, account_id)
        _audit(conn, account_id, admin, "cancel_account_deletion", "account", account_id)
    return out
