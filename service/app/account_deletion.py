"""Deleting an account under A30.1: `deleteMe`, `cancelAccountDeletion`, and the erasure job.

Written 28 September 2026 from the ruling the owner made that day.

AT THE REQUEST (deleteMe)

The account is marked deleted with the moment of the request, which stops sign-in at once
because `require_account` admits active accounts only. Every shop still connected is set
disconnected and its stored TikTok tokens are marked revoked, exactly as disconnectShop does
for one shop. Nothing is erased yet. The answer states what will happen and when, in the
words of the ruling, so the seller has a record of what they asked for.

DURING THE THIRTY DAYS (cancelAccountDeletion)

The seller signs in and cancels. The account becomes active again. Its shops stay
disconnected, because their tokens were revoked, so the seller connects them again. The
contract had no cancel operation although A30.1 rules that cancelling is possible, so the
operation was added to the contract with this module.

WHEN THE THIRTY DAYS END (erase_due, run by scripts/erase_accounts.py)

The name and email are replaced with placeholders, the identity provider's subject is
replaced so the old sign-in no longer reaches the row, the stored TikTok tokens are
overwritten, and every object under the
account's prefixes in the file store is deleted: `uploads/{shop}/`, `exports/{shop}/` and
`account-exports/{account}/`. The files go first and the rows second, so a failure part way
leaves the account due and the next run finishes it. `invoices/{shop}/` is not touched,
because A10.8 keeps the TikTok fee invoices six years, and nothing is stored there yet.

`tiktok_auth_state` rows are left. Each holds a hash of a used or expired state, its times
and the account id, and nothing that names a person. `mse_app` holds INSERT on that table
and nothing more (0021), and the first run of this job on 28 September was refused when it
tried to delete them.

The ledger, orders, costs and every other financial row stay, attached to no person, as
A30.1 rules. The retention period for them is open in A30.1, so nothing deletes them.

WHAT IS NOT BUILT, AND IS STATED RATHER THAN IMPLIED

- **Nothing runs the erasure on a schedule.** `scripts/erase_accounts.py` does the work when
  it is run. A Render cron job, or any scheduler, has to be set up by the owner.
- **A running Stripe subscription stops renewing, and is not refunded.** The owner ruled
  on 7 October 2026 that a deletion sets the subscription to end with the period already
  paid for, or with the trial, and that cancelling the deletion turns renewal back on. The
  Stripe call is made before the account is closed, and a failure refuses the deletion.
  It has run against a stand-in client only, not against the live account.
- **No email confirms the erasure**, which A3's S30 step 4 describes, because nothing in the
  service sends email.
- **TikTok is not told.** The tokens are marked revoked here and overwritten at erasure, but
  the DeauthorizeShop call is not made, for the reason disconnectShop gives.
- `invoices_retained_until` is the latest invoice's period end, or its issue date, plus six
  years. A10 keeps invoices six years from the end of the VAT period, and the VAT period is
  not stored, so this date can fall earlier than the true one. No account holds an invoice
  yet, because nothing ingests them.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import billing, storage
from .auth import Account, require_signed_in
from .db import tenant, unscoped
from .idempotency import record, replay, request_hash
from .problems import Problem

log = logging.getLogger(__name__)

router = APIRouter(tags=["Account"])

GRACE = timedelta(days=30)


class DeleteIn(BaseModel):
    confirm_email: str
    reason: str | None = Field(default=None, max_length=500)


class DeletionAcknowledgement(BaseModel):
    account_id: UUID
    scheduled_at: datetime
    includes: list[str]
    invoices_retained_until: date | None = None
    cancel_by: datetime | None = None


class CancelOut(BaseModel):
    account_id: UUID
    status: str
    shops_disconnected: int


def _london_day(moment: datetime) -> str:
    from zoneinfo import ZoneInfo

    local = moment.astimezone(ZoneInfo("Europe/London"))
    return f"{local.day} {local:%B %Y}"


def _includes(erase_at: datetime, plan_stopped: bool = False) -> list[str]:
    """What A30.1 says happens, in its own order, and the billing line the owner's ruling of
    7 October 2026 adds when the account has a plan."""
    day = _london_day(erase_at)
    plan = ([
        "Your plan stops renewing now. It ends with the period or free trial already under "
        "way, nothing more is charged, and nothing is refunded. Cancelling the deletion "
        "turns renewal back on.",
    ] if plan_stopped else [])
    return [
        "You can no longer use MyShopEdge with this account, except to cancel the deletion.",
        "Every connected shop is disconnected now, and MyShopEdge stops using its TikTok sign-in details.",
        *plan,
        f"Until {day} you can cancel the deletion by signing in again. Nothing is erased before then.",
        f"After {day} your name and email are erased, your TikTok sign-in details are "
        "erased, and every file you uploaded or exported is deleted.",
        "Your ledger stays, with your name and email removed, because financial records must "
        "be kept. MyShopEdge has not yet set when it is deleted.",
    ]


def _six_years_after(day: date) -> date:
    try:
        return day.replace(year=day.year + 6)
    except ValueError:  # 29 February
        return day.replace(year=day.year + 6, day=28)


@router.delete("/me", status_code=202, response_model=DeletionAcknowledgement,
               summary="Delete the account and its data")
def delete_me(
    body: DeleteIn,
    account: Annotated[Account, Depends(require_signed_in)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    op = "deleteMe"
    digest = request_hash(body.confirm_email.strip().lower())
    with tenant(account.id) as conn:
        again = replay(conn, account.id, op, idempotency_key, digest)
        if again:
            return JSONResponse(status_code=again[0], content=again[1])

        row = conn.execute(
            "select email::text, status, deleted_at from accounts where id = %s for update",
            (str(account.id),),
        ).fetchone()
        if row is None:
            raise Problem(401, "account_not_found", "Please sign in again.")
        email, status, deleted_at = row
        # The column is citext, so the database already treats case as no difference. The
        # check reads the address the same way, and still refuses any other address.
        if body.confirm_email.strip().lower() != email.lower():
            raise Problem(422, "validation_failed",
                          "That is not the email address on this account, so nothing was deleted.")
        if status == "suspended":
            raise Problem(403, "account_suspended", "This account is suspended.")

        renewal = "none"
        if status != "deleted":
            # Stripe goes first, inside this transaction. If it cannot be reached the
            # Problem it raises rolls the transaction back, so the seller is told nothing
            # was deleted rather than left closed and still being charged.
            renewal = billing.set_renewal_for_deletion(account.id, closing=True)
            deleted_at = conn.execute(
                "update accounts set status = 'deleted', deleted_at = now() where id = %s "
                "returning deleted_at",
                (str(account.id),),
            ).fetchone()[0]
            conn.execute(
                "update tiktok_connections set revoked_at = coalesce(revoked_at, now()) "
                "where shop_id in (select id from shops where account_id = %s)",
                (str(account.id),),
            )
            conn.execute(
                "update shops set connection_status = 'disconnected' "
                "where account_id = %s and connection_status in ('pending', 'connected', 'needs_reconnect')",
                (str(account.id),),
            )
            log.info("account %s closed for deletion", account.id)

        latest = conn.execute(
            "select max(coalesce(i.period_end, i.issued_on)) from tiktok_invoices i "
            "join shops s on s.id = i.shop_id where s.account_id = %s",
            (str(account.id),),
        ).fetchone()[0]

        erase_at = deleted_at + GRACE
        out = DeletionAcknowledgement(
            account_id=account.id, scheduled_at=erase_at,
            includes=_includes(erase_at, plan_stopped=renewal != "none"),
            invoices_retained_until=_six_years_after(latest) if latest else None,
            cancel_by=erase_at,
        )
        record(conn, account.id, op, idempotency_key, digest, 202, out.model_dump(mode="json"))
    return JSONResponse(status_code=202, content=out.model_dump(mode="json"))


@router.post("/me/deletion/cancel", response_model=CancelOut,
             summary="Cancel a requested account deletion")
def cancel_account_deletion(account: Annotated[Account, Depends(require_signed_in)]) -> CancelOut:
    with tenant(account.id) as conn:
        row = conn.execute(
            "update accounts set status = 'active', deleted_at = null "
            "where id = %s and status = 'deleted' "
            "and deleted_at > now() - interval '30 days' returning id",
            (str(account.id),),
        ).fetchone()
        if row is None:
            raise Problem(409, "not_closing", "This account has no deletion to cancel.")
        # Renewal comes back only where the deletion stopped it. A Stripe failure raises
        # and rolls back, so the account stays closing and the seller can try again.
        billing.set_renewal_for_deletion(account.id, closing=False)
        shops = conn.execute(
            "select count(*) from shops where account_id = %s and connection_status = 'disconnected'",
            (str(account.id),),
        ).fetchone()[0]
    log.info("account %s deletion cancelled", account.id)
    return CancelOut(account_id=account.id, status="active", shops_disconnected=shops)


def erase_due() -> list[dict]:
    """Erases every account whose thirty days have ended. Returns what was done, per account.

    Each account is handled on its own, so one failure leaves the others done and itself
    due for the next run.
    """
    with unscoped() as conn:
        due = [r[0] for r in conn.execute("select accounts_due_for_erasure()").fetchall()]
    done = []
    for account_id in due:
        with tenant(account_id) as conn:
            shops = [str(r[0]) for r in conn.execute(
                "select id from shops where account_id = %s", (str(account_id),)).fetchall()]
        prefixes = [f"{kind}/{s}/" for s in shops for kind in ("uploads", "exports")]
        prefixes.append(f"account-exports/{account_id}/")
        files = sum(storage.delete_prefix(p) for p in prefixes)
        with tenant(account_id) as conn:
            conn.execute(
                "update tiktok_connections set access_token_enc = '\\x'::bytea, "
                "refresh_token_enc = '\\x'::bytea, shop_cipher_enc = null, "
                "revoked_at = coalesce(revoked_at, now()) where shop_id = any(%s::uuid[])",
                (shops,),
            )
            erased = conn.execute(
                "update accounts set email = 'erased-' || id || '@erased.invalid', "
                "display_name = null, auth_subject = 'erased:' || id, erased_at = now() "
                "where id = %s and status = 'deleted' and erased_at is null returning id",
                (str(account_id),),
            ).fetchone()
        done.append({"account_id": str(account_id), "shops": len(shops), "files_deleted": files,
                     "erased": erased is not None})
        log.info("account %s erased: %s", account_id, done[-1])
    return done
