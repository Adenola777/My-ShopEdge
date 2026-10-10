"""Which notices are emailed, and the sweep that sends them. Written 10 October 2026.

Needs migration 0031. **Unverified against Resend**, like `mailer.py`: the sweep has run only
against a local PostgreSQL 16 and a stand-in for Resend (`testdata/notice_email_check.py`).

WHICH NOTICES ARE EMAILED

Every notice is still written to the notification centre (NTF-1). Five types are also emailed,
each for a reason on the record:

  * `connection_revoked`, critical, the seller deauthorised the app in TikTok. NTF-2 names
    "connection revoked".
  * `connection_lapsed`, critical, a token refresh failed after the access token had lapsed,
    so nothing can be read from the shop. NTF-2 names "feed failing".
  * `reconnect_needed`, warning, TikTok said the authorisation is about to expire. **Derived,
    not ruled:** it is the warning before the feed fails, so it is treated as part of NTF-2.
  * `order_limit_passed`, warning. A16.3: at 100 per cent "an email is sent".
  * `scheduled_export_ready`, info. A5.7: the seller "is told in the app and, if they have not
    opted out, by email".
  * `account_suspended`, critical, and `account_reactivated`, info, written by the admin's
    actions. A34.8 ruling 3: the seller is told. A suspension notice is the one notice emailed
    to an account that is not active, because a suspended seller cannot open the app to read
    it. Added 10 October 2026.

The rest, `low_stock`, `return_unchecked`, `first_read_complete` and `stock_absorbed`, stay in
the app, because the SRD's interfaces table says "Transactional email for verification and
critical notices only". A type added later is not emailed until it is named here.

WHEN A NOTICE IS NOT SENT

A notice is marked `not_emailed`, with the reason in `email_note`, when its type is not listed
above, when the seller has switched email off (NTF-2's acceptance: "Opted-out sellers receive no
email"), when the account is closing, when the seller marked it done before it was sent, or when
it is more than three days old when first tried. The last rule exists so that a sender that was
unconfigured for a while does not deliver a backlog of stale news when it starts.

While `RESEND_API_KEY` is unset the sweep does nothing and leaves every notice pending.

SENDING ONCE

Each notice is sent in its own `tenant()` transaction, locked with `for update skip locked`, so
the daily job and a webhook's sweep never both send it. A process that dies after Resend
accepted the email and before the commit leaves the notice pending, and the next attempt reuses
the idempotency key `notice-<id>`, which Resend honours for 24 hours. A refusal is counted, and
the third marks the notice `failed`.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from . import db, mailer

logger = logging.getLogger("myshopedge.notice_email")

EMAILED_TYPES = frozenset({
    "connection_revoked",
    "connection_lapsed",
    "reconnect_needed",
    "order_limit_passed",
    "scheduled_export_ready",
    "account_suspended",
    "account_reactivated",
})
# The one type emailed to an account whose status is `suspended` (A34.8 ruling 3).
SENT_WHILE_SUSPENDED = frozenset({"account_suspended"})
MAX_AGE = timedelta(days=3)
MAX_ATTEMPTS = 3
DEFAULT_APP_URL = "https://app.myshopedge.inspirecraftglobal.com"


def app_url() -> str:
    return (os.environ.get("APP_BASE_URL") or DEFAULT_APP_URL).rstrip("/")


def compose(notice: dict[str, Any]) -> tuple[str, str]:
    """The subject and plain text of one notice's email. The words are the notice's own, so the
    email never says anything the notification centre does not."""
    if notice["shop_id"]:
        link = f"{app_url()}/shops/{notice['shop_id']}/notifications"
    else:
        link = f"{app_url()}/shops"
    lines = [notice["title"], ""]
    if notice["body"]:
        lines += [notice["body"], ""]
    lines += [
        f"You can see this notice in MyShopEdge: {link}",
        "",
        "MyShopEdge sends this email because email notices are switched on for your account. "
        "You can switch them off in Settings, under Profile and plan.",
        "",
        "MyShopEdge is run by Inspirecraft Global Ltd, Leicester.",
    ]
    return notice["title"], "\n".join(lines)


def _reason_not_to_send(notice: dict[str, Any], account: dict[str, Any],
                        now: datetime) -> str | None:
    if notice["type"] not in EMAILED_TYPES:
        return "this type of notice is shown in the app only"
    if account["status"] != "active" and not (
            account["status"] == "suspended" and notice["type"] in SENT_WHILE_SUSPENDED):
        return "the account is not active"
    if not account["email_notices"]:
        return "the seller has switched email notices off"
    if notice["status"] == "done":
        return "the seller marked the notice done before it was emailed"
    if notice["created_at"] < now - MAX_AGE:
        return "the notice was more than three days old when first tried"
    return None


def _set(conn, notice_id: UUID, status: str, note: str | None, attempts: int,
         emailed_at: datetime | None = None) -> None:
    conn.execute(
        "update notifications set email_status = %s, email_note = %s, email_attempts = %s, "
        "emailed_at = %s where id = %s",
        (status, note, attempts, emailed_at, str(notice_id)))


def send_for_account(account_id: UUID | str, now: datetime | None = None,
                     transport: mailer.Transport | None = None) -> dict[str, int]:
    """Considers every pending notice on one account. Returns counts by outcome."""
    now = now or datetime.now(timezone.utc)
    counts = {"sent": 0, "not_emailed": 0, "failed": 0, "retry": 0}
    with db.tenant(account_id) as conn:
        ids = [r[0] for r in conn.execute(
            "select id from notifications where email_status = 'pending' "
            "order by created_at, id").fetchall()]
    for notice_id in ids:
        with db.tenant(account_id) as conn:
            cur = conn.execute(
                "select id, shop_id, type, title, body, status, created_at, email_attempts "
                "from notifications where id = %s and email_status = 'pending' "
                "for update skip locked", (str(notice_id),))
            row = cur.fetchone()
            if row is None:
                continue
            notice = dict(zip([d.name for d in cur.description], row, strict=True))
            cur = conn.execute(
                "select email::text as email, status, email_notices from accounts where id = %s",
                (str(account_id),))
            arow = cur.fetchone()
            account = dict(zip([d.name for d in cur.description], arow, strict=True))
            reason = _reason_not_to_send(notice, account, now)
            if reason:
                _set(conn, notice_id, "not_emailed", reason, notice["email_attempts"])
                counts["not_emailed"] += 1
                continue
            subject, text = compose(notice)
            attempts = notice["email_attempts"] + 1
            try:
                sent_id = mailer.send(account["email"], subject, text, f"notice-{notice_id}",
                                      transport)
            except mailer.MailError as err:
                final = attempts >= MAX_ATTEMPTS
                _set(conn, notice_id, "failed" if final else "pending",
                     f"{err.code}: {err.message}", attempts)
                counts["failed" if final else "retry"] += 1
                logger.warning("notice email %s refused (%s), attempt %s", notice_id, err.code,
                               attempts)
                continue
            _set(conn, notice_id, "sent", sent_id, attempts, now)
            counts["sent"] += 1
    return counts


def send_due(now: datetime | None = None,
             transport: mailer.Transport | None = None) -> dict[str, Any]:
    """The daily sweep across every account with a pending notice."""
    if not mailer.configured():
        return {"state": "unconfigured"}
    with db.unscoped() as conn:
        accounts = [r[0] for r in conn.execute("select account_id from notices_due_for_email()")]
    totals = {"sent": 0, "not_emailed": 0, "failed": 0, "retry": 0}
    errors = 0
    for account_id in accounts:
        try:
            counts = send_for_account(account_id, now, transport)
        except Exception:  # noqa: BLE001  one account's fault must not stop the others
            logger.exception("notice email sweep failed for account %s", account_id)
            errors += 1
            continue
        for k, v in counts.items():
            totals[k] += v
    return {"state": "ran", "accounts": len(accounts), "errors": errors, **totals}


def send_now(account_id: UUID | str, transport: mailer.Transport | None = None) -> None:
    """Called after a webhook writes a notice, so a revoked or expiring connection is emailed
    within minutes rather than at the next daily run. Never raises: the webhook's own work is
    already done, and the daily sweep picks up anything left pending."""
    if not mailer.configured():
        return
    try:
        send_for_account(account_id, transport=transport)
    except Exception:  # noqa: BLE001
        logger.exception("notice email after webhook failed for account %s", account_id)
