"""Sends one email through Postmark. Written 10 October 2026, when the owner chose Resend, and
moved to Postmark the same day on the owner's instruction, because Resend's domain check had not
started.

**UNVERIFIED AGAINST POSTMARK.** Nothing in this file has sent a real email. It has run only
against the stand-in transports in `testdata/notice_email_check.py` and `testdata/admin_check.py`.
No Postmark server, token or sender domain existed when it was written, and Postmark will refuse
a send from `myshopedge.inspirecraftglobal.com` until that domain is verified there.

WHAT IS FACT AND WHAT IS NOT

  * Postmark's own website could not be read from the session that wrote this, because the
    network policy refused `postmarkapp.com`. Every fact below was read instead from Postmark's
    official Node client, the npm package `postmark` 5.1.0 (repository
    `github.com/ActiveCampaign/postmark.js`), downloaded on 10 October 2026:
      - `HttpClient` builds requests on `https://api.postmarkapp.com`, and
        `ServerClient.sendEmail` posts the message to `/email`.
      - A server token travels in the header `X-Postmark-Server-Token`, with `Accept` and
        `Content-Type` both `application/json`.
      - The `Message` model names `From` and `Subject` as required, and `To`, `TextBody`,
        `MessageStream`, `TrackOpens`, `TrackLinks` and `Metadata` as optional. `TrackLinks`
        takes `None` among its values.
      - A success is a `MessageSendingResponse` carrying `MessageID`, `SubmittedAt`,
        `ErrorCode` and `Message`. A refusal is read from the body's `ErrorCode` and `Message`.
      - The client's integration tests read a message stream named `outbound`.
  * **Not established:** that every server has a stream named `outbound`, and whether Postmark
    sends anything when `ErrorCode` is not 0 on a 200. `send` treats a 2xx with an `ErrorCode`
    other than 0 as a refusal, and `POSTMARK_MESSAGE_STREAM` overrides the stream.
  * **Postmark has no idempotency key** in that client, unlike Resend. `reference` travels as
    metadata so a sent email can be traced to its notice, and it does not stop a repeat. See
    `notice_email` on what that means for sending once.
  * Opens and links are not tracked. Both are switched off in every message rather than left
    to the server's settings, because the Privacy Policy names no tracking of notice emails.

THE VARIABLES

  * `POSTMARK_SERVER_TOKEN` is the server's API token. It is the owner's to set on
    `My-ShopEdge-1` and on the sync cron, and it is never read into a message or a log.
  * `EMAIL_FROM` overrides the sender. Unset, it is `MyShopEdge <notices@myshopedge.
    inspirecraftglobal.com>`, which needs the domain, or that address, verified in Postmark.
  * `POSTMARK_MESSAGE_STREAM` overrides the stream, which is `outbound` when unset.
"""

from __future__ import annotations

import os
from typing import Any, Callable

import httpx

POSTMARK_URL = "https://api.postmarkapp.com/email"
DEFAULT_FROM = "MyShopEdge <notices@myshopedge.inspirecraftglobal.com>"
DEFAULT_STREAM = "outbound"
HTTP_TIMEOUT = 15.0


class MailError(Exception):
    """Postmark refused the email or could not be reached. `code` is Postmark's HTTP status,
    with its `ErrorCode` after a slash where it gave one, or `unreachable`, and `message` is
    Postmark's own text where it gave one."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


Transport = Callable[[str, dict[str, str], dict[str, Any]], tuple[int, dict[str, Any]]]


def configured() -> bool:
    return bool(os.environ.get("POSTMARK_SERVER_TOKEN"))


def sender() -> str:
    return os.environ.get("EMAIL_FROM") or DEFAULT_FROM


def http_transport(url: str, headers: dict[str, str],
                   payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=HTTP_TIMEOUT)
    except httpx.HTTPError as err:
        raise MailError("unreachable", "Postmark did not answer.") from err
    try:
        body = response.json() if response.content else {}
    except ValueError:
        body = {}
    return response.status_code, body if isinstance(body, dict) else {}


def send(to: str, subject: str, text: str, reference: str,
         transport: Transport | None = None) -> str | None:
    """Sends one plain text email and returns Postmark's `MessageID` for it, or None if none
    was given. `reference` is kept with the message as metadata and does not prevent a repeat."""
    token = os.environ.get("POSTMARK_SERVER_TOKEN")
    if not token:
        raise MailError("unconfigured", "POSTMARK_SERVER_TOKEN is not set.")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Postmark-Server-Token": token,
    }
    payload = {
        "From": sender(),
        "To": to,
        "Subject": subject,
        "TextBody": text,
        "MessageStream": os.environ.get("POSTMARK_MESSAGE_STREAM") or DEFAULT_STREAM,
        "TrackOpens": False,
        "TrackLinks": "None",
        "Metadata": {"reference": reference},
    }
    status, body = (transport or http_transport)(POSTMARK_URL, headers, payload)
    error_code = body.get("ErrorCode")
    if not 200 <= status < 300 or error_code not in (None, 0):
        code = f"{status}/{error_code}" if error_code not in (None, 0) else str(status)
        message = body.get("Message") or "Postmark refused the email."
        raise MailError(code, str(message)[:500])
    sent_id = body.get("MessageID")
    return str(sent_id) if sent_id else None
