"""Sends one email through Resend. Written 10 October 2026, when the owner chose Resend.

**UNVERIFIED AGAINST RESEND.** Nothing in this file has sent a real email. It has run only
against the stand-in transport in `testdata/notice_email_check.py`. The sending domain
`myshopedge.inspirecraftglobal.com` was registered with Resend on 9 October 2026, in region
eu-west-1, and its status read `not_started` at 21:11 UTC that day, so Resend would refuse a
send from it until the owner's DNS records are verified.

WHAT IS FACT AND WHAT IS NOT

  * Read from Resend's own page "Send Email" (`resend.com/docs/api-reference/emails/send-email`),
    fetched through a Render one-off job on 10 October 2026: `from`, `to`, `subject` are
    required; `from` may carry a name as `Name <address>`; `text` is the plain text version;
    the `Idempotency-Key` header prevents duplicated emails, is at most 256 characters, and
    expires after 24 hours.
  * Called on 9 October 2026 from a Render one-off job: `GET https://api.resend.com/domains`
    with `Authorization: Bearer <RESEND_API_KEY>` answered with the domain, so the key and the
    host are right.
  * **Not read from the page:** the path `POST /emails` and that a success answers with an
    `id`. The page's text was cut off before its request line and response example. Both are
    what Resend's examples are generally known to show, and the first real send settles them.
    `send` treats any 2xx as accepted and keeps the `id` only if one is given.

THE VARIABLES

  * `RESEND_API_KEY` is set on `My-ShopEdge-1` and on the sync cron (checked by name only).
    The key is never read into a message or a log.
  * `EMAIL_FROM` overrides the sender. Unset, it is `MyShopEdge <notices@myshopedge.
    inspirecraftglobal.com>`. Resend accepts any local part on a verified domain, so the
    address needs no mailbox.
"""

from __future__ import annotations

import os
from typing import Any, Callable

import httpx

RESEND_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "MyShopEdge <notices@myshopedge.inspirecraftglobal.com>"
HTTP_TIMEOUT = 15.0


class MailError(Exception):
    """Resend refused the email or could not be reached. `code` is Resend's HTTP status, or
    `unreachable`, and `message` is Resend's own text where it gave one."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


Transport = Callable[[str, dict[str, str], dict[str, Any]], tuple[int, dict[str, Any]]]


def configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


def sender() -> str:
    return os.environ.get("EMAIL_FROM") or DEFAULT_FROM


def http_transport(url: str, headers: dict[str, str],
                   payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=HTTP_TIMEOUT)
    except httpx.HTTPError as err:
        raise MailError("unreachable", "Resend did not answer.") from err
    try:
        body = response.json() if response.content else {}
    except ValueError:
        body = {}
    return response.status_code, body if isinstance(body, dict) else {}


def send(to: str, subject: str, text: str, idempotency_key: str,
         transport: Transport | None = None) -> str | None:
    """Sends one plain text email and returns Resend's id for it, or None if none was given.

    The idempotency key makes a repeat within 24 hours a no-op at Resend, so a run that sent
    and then failed before recording it does not send twice on the next attempt that day."""
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        raise MailError("unconfigured", "RESEND_API_KEY is not set.")
    if len(idempotency_key) > 256:
        raise ValueError("Resend's idempotency key is at most 256 characters.")
    headers = {
        "Authorization": f"Bearer {key}",
        "Idempotency-Key": idempotency_key,
    }
    payload = {"from": sender(), "to": [to], "subject": subject, "text": text}
    status, body = (transport or http_transport)(RESEND_URL, headers, payload)
    if not 200 <= status < 300:
        message = body.get("message") or body.get("error") or "Resend refused the email."
        raise MailError(str(status), str(message)[:500])
    sent_id = body.get("id")
    return str(sent_id) if sent_id else None
