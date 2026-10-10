"""The TikTok Shop webhook receiver.

Built 7 October 2026 to close the second ground of the Go Live rejection. The PRD's sync
design uses TikTok Shop webhooks, and the contract names this endpoint, but it had not been
built. It is the one operation the contract's own introduction listed as missing.

WHAT IS A FACT HERE (from TikTok's webhook configuration guide, pasted by the owner on
7 October 2026):

  * The signature is HMAC-SHA256, with the app secret as the key, over the bytes
    `app_key + raw_request_body`, with no reformatting of the body, compared as a lowercase
    hexadecimal string against the `Authorization` header. This is a different algorithm from
    `connections._sign`, which signs the service's own outbound API calls.
  * The receiver must return HTTP 200 with an empty body within three seconds to acknowledge,
    and 401 only when the signature fails. Any other response, or a timeout, is a failed
    delivery that TikTok retries.
  * Delivery is at least once, so processing is idempotent. TikTok's guide says to
    de-duplicate on `tts_notification_id` when present.

So the receiver verifies the signature, records the event under a de-duplication key,
acknowledges within the three seconds, and does the real work in a background task. That
background work is what makes an event update the corresponding data, which is TikTok's
second requirement.

UNVERIFIED, BY NAME. The Webhooks overview payload schema is not in this repository, so the
exact field names that carry the event type, the shop id and the notification id are not a
recorded fact. The receiver reads each from the most likely keys, and falls back to a hash of
the raw body for the de-duplication key, so an identical redelivery is always dropped whatever
the field names turn out to be. The signature algorithm, which is the part that must be exact,
is recorded. The data-update behaviour is checked against crafted payloads only, because no
real TikTok event has reached this receiver (the same standing as the rest of the TikTok code).

Since 10 October 2026 a deauthorisation also writes a `connection_revoked` notice, which NTF-2
names, and after a deauthorisation or an expiry warning the account's pending notices are
emailed at once through `notice_email.send_now` rather than at the next daily run.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Header, Request, Response
from psycopg.types.json import Jsonb

from . import db, notice_email
from .problems import Problem

logger = logging.getLogger("myshopedge.tiktok_webhook")

router = APIRouter(tags=["Connection"])

# A webhook-triggered sync reads a short recent window. Everything it writes is idempotent, so
# a window that overlaps the daily cron sync changes nothing.
WINDOW_DAYS = 7


def webhook_signature(app_key: str, app_secret: str, raw: bytes) -> str:
    """HMAC-SHA256(key=app_secret, message=app_key + raw_body), lowercase hex."""
    message = app_key.encode("utf-8") + raw
    return hmac.new(app_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def signature_ok(header: str | None, app_key: str, app_secret: str, raw: bytes) -> bool:
    if not header:
        return False
    expected = webhook_signature(app_key, app_secret, raw)
    return hmac.compare_digest(expected, header.strip().lower())


def classify(event_type: str) -> str:
    """The family of work an event needs. The tokens are matched case-insensitively so a new
    event name in the same family is handled without a code change."""
    e = (event_type or "").upper()
    if "DEAUTHOR" in e:
        return "deauthorization"
    if "AUTHORIZATION" in e and "EXPIR" in e:
        return "authorization_expiring"
    if any(tok in e for tok in (
            "ORDER", "PACKAGE", "FULFIL", "RETURN", "REFUND", "REPLACEMENT",
            "PRODUCT", "INVENTORY", "CANCEL")):
        return "sync"
    return "other"


def _event_type(payload: dict[str, Any]) -> str:
    return str(payload.get("type") or payload.get("event_type") or payload.get("topic") or "")


def _shop_tiktok_id(payload: dict[str, Any]) -> str | None:
    if payload.get("shop_id"):
        return str(payload["shop_id"])
    data = payload.get("data")
    if isinstance(data, dict) and data.get("shop_id"):
        return str(data["shop_id"])
    return None


def _notification_id(payload: dict[str, Any]) -> str | None:
    if payload.get("tts_notification_id"):
        return str(payload["tts_notification_id"])
    data = payload.get("data")
    if isinstance(data, dict) and data.get("tts_notification_id"):
        return str(data["tts_notification_id"])
    return None


def claim(dedupe_key: str, notification_id: str | None, event_type: str,
          shop_tiktok_id: str | None, payload: dict[str, Any]):
    """Record the event if new, and resolve its shop and account. Returns (is_new, shop_id,
    account_id). Runs before an account is known, so it goes through the SECURITY DEFINER
    function (0028), the same way `resolve_account` is called."""
    with db.unscoped() as conn:
        row = conn.execute(
            "select is_new, shop_id, account_id from "
            "claim_tiktok_webhook(%s, %s, %s, %s, %s)",
            (dedupe_key, notification_id, event_type, shop_tiktok_id, Jsonb(payload)),
        ).fetchone()
    return (row[0], row[1], row[2]) if row else (False, None, None)


def mark(dedupe_key: str, status: str, note: str) -> None:
    with db.unscoped() as conn:
        conn.execute("select mark_tiktok_webhook(%s, %s, %s)", (dedupe_key, status, note))


def process_event(dedupe_key: str, account_id: str, shop_id: str, event_type: str,
                  transport=None, now: datetime | None = None) -> None:
    """The work an event triggers, run after the 200 is sent. Each branch records its outcome
    through `mark`, so the webhook log shows what happened."""
    from .tiktok_api import TikTokError, client_for, http_transport, refresh_connection
    from .tiktok_sync import sync_shop

    transport = transport or http_transport
    now = now or datetime.now(timezone.utc)
    kind = classify(event_type)
    try:
        if kind == "deauthorization":
            with db.tenant(account_id) as conn:
                conn.execute("update shops set connection_status = 'disconnected' where id = %s",
                             (shop_id,))
                conn.execute("update tiktok_connections set revoked_at = coalesce(revoked_at, now()) "
                             "where shop_id = %s", (shop_id,))
                # NTF-2 names a revoked connection as a critical event to tell the seller
                # about. Keyed on the event, so a redelivery of the same event adds nothing.
                conn.execute(
                    "insert into notifications (account_id, shop_id, type, severity, title, body, "
                    "entity_type, entity_id, dedupe_key) values "
                    "(%s, %s, 'connection_revoked', 'critical', %s, %s, 'shop', %s, %s) "
                    "on conflict (account_id, dedupe_key) do nothing",
                    (account_id, shop_id,
                     "Your TikTok Shop is no longer connected to MyShopEdge.",
                     "TikTok told MyShopEdge that the shop removed its access. MyShopEdge can no "
                     "longer read orders or payouts for this shop. Connect the shop again to "
                     "carry on.",
                     shop_id, f"connection_revoked:{shop_id}:{dedupe_key}"))
            mark(dedupe_key, "done", "seller deauthorised: shop disconnected and tokens revoked")
            notice_email.send_now(account_id)
            return

        if kind == "authorization_expiring":
            with db.tenant(account_id) as conn:
                conn.execute(
                    "update shops set connection_status = 'needs_reconnect' "
                    "where id = %s and connection_status in ('connected', 'pending')", (shop_id,))
                conn.execute(
                    "insert into notifications (account_id, shop_id, type, severity, title, body, "
                    "entity_type, entity_id, dedupe_key) values "
                    "(%s, %s, 'reconnect_needed', 'warning', %s, %s, 'shop', %s, %s) "
                    "on conflict (account_id, dedupe_key) do nothing",
                    (account_id, shop_id,
                     "Your TikTok Shop connection is close to expiring.",
                     "Reconnect your shop so MyShopEdge keeps reading your orders and payouts.",
                     shop_id, f"reconnect_needed:{shop_id}"))
            mark(dedupe_key, "done", "authorisation expiring: shop marked needs_reconnect")
            notice_email.send_now(account_id)
            return

        if kind == "sync":
            from .tiktok_sync import may_sync
            if not may_sync(account_id, shop_id, now):
                mark(dedupe_key, "skipped", "account state does not allow reading (A36)")
                return
            with db.tenant(account_id) as conn:
                refresh_connection(conn, shop_id, now, transport)
            with db.tenant(account_id) as conn:
                status = conn.execute("select connection_status from shops where id = %s",
                                      (shop_id,)).fetchone()[0]
                if status == "needs_reconnect":
                    mark(dedupe_key, "skipped", "shop needs reconnect, nothing synced")
                    return
                client = client_for(conn, shop_id, transport)
                outcome = sync_shop(conn, shop_id, client, now - timedelta(days=WINDOW_DAYS),
                                    now, kind="webhook")
            mark(dedupe_key, "done", f"synced: {outcome}")
            return

        mark(dedupe_key, "ignored", f"no handler for event {event_type!r}")
    except TikTokError as err:
        mark(dedupe_key, "failed", f"{err.code}: {err.message}")
    except Exception as err:  # noqa: BLE001  the background task must not crash the process
        logger.exception("tiktok webhook processing failed for %s", dedupe_key)
        try:
            mark(dedupe_key, "failed", f"{type(err).__name__}: {err}")
        except Exception:  # noqa: BLE001
            logger.exception("tiktok webhook: could not record the failure for %s", dedupe_key)


@router.post("/webhooks/tiktok", summary="TikTok Shop events", include_in_schema=True)
async def receive_tiktok_webhook(
    request: Request,
    background: BackgroundTasks,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> Response:
    """Authenticated by the webhook signature header rather than by a bearer token, which is
    why the security requirement is empty. Verifies, records for de-duplication, acknowledges
    within three seconds, and does the work in a background task."""
    app_key = os.environ.get("TIKTOK_APP_KEY")
    app_secret = os.environ.get("TIKTOK_APP_SECRET")
    raw = await request.body()

    if not app_key or not app_secret:
        # The service cannot verify the signature, so it cannot accept the notification. This
        # never happens on the configured service; the two variables are set there.
        raise Problem(503, "webhook_unconfigured", "The webhook receiver is not configured.")

    if not signature_ok(authorization, app_key, app_secret, raw):
        return Response(status_code=401)

    try:
        payload = json.loads(raw) if raw else {}
        if not isinstance(payload, dict):
            payload = {}
    except ValueError:
        payload = {}

    event_type = _event_type(payload)
    shop_tiktok_id = _shop_tiktok_id(payload)
    notification_id = _notification_id(payload)
    # TikTok's guide prefers tts_notification_id; a hash of the raw body is the stable
    # fallback, so an identical redelivery always carries the same key.
    dedupe_key = notification_id or ("sha256:" + hashlib.sha256(raw).hexdigest())

    try:
        is_new, shop_id, account_id = claim(
            dedupe_key, notification_id, event_type, shop_tiktok_id, payload)
    except Exception:  # noqa: BLE001  a store failure must not make TikTok retry a valid event
        logger.exception("tiktok webhook: could not record the event")
        return Response(status_code=200)

    if is_new and shop_id is not None and account_id is not None:
        background.add_task(process_event, dedupe_key, str(account_id), str(shop_id), event_type)
    elif is_new:
        # Recorded, but for a shop this installation does not hold: acknowledge and ignore, the
        # way the Stripe webhook treats an unknown customer.
        try:
            mark(dedupe_key, "ignored", f"no shop for tiktok id {shop_tiktok_id}")
        except Exception:  # noqa: BLE001
            logger.exception("tiktok webhook: could not mark an unknown-shop event")

    return Response(status_code=200)
