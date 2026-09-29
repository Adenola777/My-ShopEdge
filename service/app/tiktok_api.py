"""Reading a connected shop from TikTok, and keeping its access token alive.

Part 1 of the batch approved on 29 September 2026. `connections.py` makes the connection;
this module uses it.

**Unverified against a live call.** No request built here has reached TikTok. The signing
is `connections._sign`, which has never made a live call either. Everything here has run
only against recorded and generated payloads through `Transport`, so the first real run is
its test. What each constant rests on is stated beside it, and the ones that rest on
nothing recorded in this repository are listed in UNVERIFIED below, by name.

WHAT IS A FACT HERE

  * The refresh call, its host, its four parameters and its response shape: A23.4, read from
    TikTok's authorisation page.
  * The access token lives seven days: A23.4.
  * `sort_field` is required on every finance endpoint and TikTok does not refuse a wrong
    value, it silently sorts by something else. The permitted value per path: A19.4, from
    TikTok's OpenAPI specification. So `get` refuses a value not on that list.
  * The default `sort_order` differs between endpoints (A19.4), so it is always sent.
  * An empty time filter has undefined behaviour (A19.4), so every listing sends a lower bound.
  * `page_size` accepts 1 to 100 (A11.4). `shop_cipher` is sent on every shop call (A11.4).
  * Finance responses carry `next_page_token`: the recorded 202501 payload in
    `testdata/real_payloads/statement_transactions_202501.json`.

UNVERIFIED, BY NAME

  * `PAGE_TOKEN_PARAM`, the query parameter that carries `next_page_token` back. The
    response field is recorded; the request parameter's name is not.
  * `ORDER_DETAIL_IDS_PARAM` and `ORDER_DETAIL_MAX_IDS`, for Get Order Detail.
  * The body fields of the two search calls, `ORDER_SEARCH_BODY` and `RETURN_SEARCH_BODY`.
  * Where the page size goes on the two POST searches: sent as a query parameter here.
"""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterator
from uuid import UUID

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .connections import API_BASE, HTTP_TIMEOUT, REFRESH_URL, _encrypt, _sign, expiry

# A19.4. The value each path accepts for `sort_field`. A path absent here takes none.
SORT_FIELDS = {
    "/finance/202309/statements": {"statement_time"},
    "/finance/202501/statements/{id}/statement_transactions": {"order_create_time"},
    "/finance/202507/orders/unsettled": {"order_create_time"},
    "/order/202309/orders/search": {"create_time", "update_time"},
    "/return_refund/202309/returns/search": {"create_time", "update_time"},
}

STATEMENTS_PATH = "/finance/202309/statements"                                  # A11.4, A17.2
STATEMENT_TXNS_PATH = "/finance/202501/statements/{id}/statement_transactions"  # A17.1
ORDER_CALC_PATH = "/finance/202501/orders/{id}/statement_transactions"           # A11.2, A17.2
ORDER_SEARCH_PATH = "/order/202309/orders/search"                                # A11.4
ORDER_DETAIL_PATH = "/order/202309/orders"                                       # A11.4
RETURN_SEARCH_PATH = "/return_refund/202309/returns/search"                      # A11.4

PAGE_SIZE = 100                  # A11.4: 1 to 100
PAGE_TOKEN_PARAM = "page_token"  # UNVERIFIED
ORDER_DETAIL_IDS_PARAM = "ids"   # UNVERIFIED
ORDER_DETAIL_MAX_IDS = 50        # UNVERIFIED
ORDER_SEARCH_BODY = ("update_time_ge", "update_time_lt")    # UNVERIFIED
RETURN_SEARCH_BODY = ("update_time_ge", "update_time_lt")   # UNVERIFIED

# A23.4 gives the access token seven days. A refresh is attempted once fewer than two days
# are left, so a job that fails on one day has at least one more daily run to succeed in
# before the token lapses.
REFRESH_WHEN_LEFT = timedelta(days=2)


class TikTokError(Exception):
    """TikTok answered, and refused. `code` is TikTok's own, verbatim, or the HTTP status."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


# A transport sends one request and returns TikTok's JSON body. The real one is httpx; the
# tests pass one that answers from recorded payloads, so the same code path runs in both.
Transport = Callable[[str, str, dict[str, str], dict[str, str], bytes | None], dict[str, Any]]


def http_transport(method: str, url: str, params: dict[str, str], headers: dict[str, str],
                   body: bytes | None) -> dict[str, Any]:
    try:
        response = httpx.request(method, url, params=params, headers=headers, content=body,
                                 timeout=HTTP_TIMEOUT)
    except httpx.HTTPError as err:
        raise TikTokError("unreachable", "TikTok did not answer.") from err
    try:
        payload = response.json() if response.content else {}
    except ValueError:
        payload = {}
    if response.status_code != 200 and "code" not in payload:
        raise TikTokError(str(response.status_code), "TikTok answered with an HTTP error.")
    return payload


def _key() -> bytes:
    raw = os.environ.get("TIKTOK_TOKEN_KEY")
    if not raw:
        raise RuntimeError("TIKTOK_TOKEN_KEY is not set.")
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise RuntimeError("TIKTOK_TOKEN_KEY is not 32 bytes.")
    return key


def decrypt(blob: bytes) -> str:
    """The inverse of `connections._encrypt`: a 12 byte nonce, then AES-256-GCM."""
    blob = bytes(blob)
    return AESGCM(_key()).decrypt(blob[:12], blob[12:], None).decode("utf-8")


def _template(path: str) -> str:
    """The path with any identifier put back as `{id}`, to look up its sort field."""
    for template in SORT_FIELDS:
        head, _, tail = template.partition("{id}")
        if tail and path.startswith(head) and path.endswith(tail):
            return template
    return path


@dataclass
class Client:
    access_token: str
    shop_cipher: str | None
    transport: Transport = http_transport
    app_key: str | None = None
    app_secret: str | None = None

    def __post_init__(self) -> None:
        self.app_key = self.app_key or os.environ.get("TIKTOK_APP_KEY")
        self.app_secret = self.app_secret or os.environ.get("TIKTOK_APP_SECRET")
        if not self.app_key or not self.app_secret:
            raise RuntimeError("TIKTOK_APP_KEY and TIKTOK_APP_SECRET must both be set.")

    def call(self, method: str, path: str, query: dict[str, str] | None = None,
             body: dict[str, Any] | None = None) -> dict[str, Any]:
        params = {k: str(v) for k, v in (query or {}).items()}
        allowed = SORT_FIELDS.get(_template(path))
        if allowed is not None:
            if params.get("sort_field") not in allowed:
                raise ValueError(f"{path} takes sort_field in {sorted(allowed)}, "
                                 f"not {params.get('sort_field')!r}")
            if params.get("sort_order") not in ("ASC", "DESC"):
                raise ValueError(f"{path} must be sent an explicit sort_order")
        if self.shop_cipher:
            params["shop_cipher"] = self.shop_cipher
        params["app_key"] = self.app_key
        # Ten digits, seconds. A millisecond timestamp is refused (connections._signed_get).
        params["timestamp"] = str(int(time.time()))
        raw = json.dumps(body, separators=(",", ":")).encode("utf-8") if body is not None else b""
        params["sign"] = _sign(path, params, raw, self.app_secret)
        answer = self.transport(method, f"{API_BASE}{path}", params,
                                {"x-tts-access-token": self.access_token,
                                 "content-type": "application/json"},
                                raw if body is not None else None)
        if answer.get("code") != 0:
            raise TikTokError(str(answer.get("code")), str(answer.get("message") or ""))
        return answer.get("data") or {}

    def pages(self, method: str, path: str, query: dict[str, str],
              body: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        """Every page of a listing. Stops on an empty or absent `next_page_token`."""
        token = None
        seen: set[str] = set()
        while True:
            q = dict(query, page_size=str(PAGE_SIZE))
            if token:
                q[PAGE_TOKEN_PARAM] = token
            data = self.call(method, path, q, body)
            yield data
            token = data.get("next_page_token") or None
            if not token:
                return
            if token in seen:
                # A token handed back twice would loop for ever and bill the rate limit.
                raise TikTokError("page_loop", f"{path} returned the same page token twice.")
            seen.add(token)


def refresh_due(access_expires_at: datetime | None, now: datetime) -> bool:
    return access_expires_at is None or access_expires_at - now < REFRESH_WHEN_LEFT


def refresh_tokens(refresh_token: str, transport: Transport = http_transport) -> dict[str, Any]:
    """A23.4. Same host as the exchange, and the response has the exchange's shape."""
    params = {
        "app_key": os.environ.get("TIKTOK_APP_KEY") or "",
        "app_secret": os.environ.get("TIKTOK_APP_SECRET") or "",
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    if not params["app_key"] or not params["app_secret"]:
        raise RuntimeError("TIKTOK_APP_KEY and TIKTOK_APP_SECRET must both be set.")
    answer = transport("GET", REFRESH_URL, params, {}, None)
    data = answer.get("data") or {}
    if answer.get("code") != 0 or not data.get("access_token"):
        raise TikTokError(str(answer.get("code")), str(answer.get("message") or "refused"))
    return data


def refresh_connection(conn, shop_id: UUID | str, now: datetime | None = None,
                       transport: Transport = http_transport) -> str:
    """Refresh one shop's tokens when due. Runs inside the shop's `tenant()` transaction.

    Returns `not_due`, `refreshed` or `failed`. A failure is recorded with TikTok's own code
    and message (0022), which is what Needs you reads. When the access token has already
    lapsed the shop is marked `needs_reconnect`, because nothing can be read from it.
    """
    now = now or datetime.now(timezone.utc)
    row = conn.execute(
        "select refresh_token_enc, access_expires_at from tiktok_connections "
        "where shop_id = %s and revoked_at is null", (str(shop_id),)).fetchone()
    if row is None:
        return "not_due"
    if not refresh_due(row[1], now):
        return "not_due"
    try:
        data = refresh_tokens(decrypt(row[0]), transport)
    except TikTokError as err:
        conn.execute(
            "update tiktok_connections set refresh_attempted_at = %s, refresh_failure_code = %s, "
            "refresh_failure_reason = %s where shop_id = %s",
            (now, err.code, err.message[:500], str(shop_id)))
        if row[1] is None or row[1] <= now:
            conn.execute("update shops set connection_status = 'needs_reconnect' where id = %s",
                         (str(shop_id),))
        return "failed"
    # The same fields as the code exchange, read the same way. That the refresh answer also
    # carries Unix times is UNVERIFIED: no refresh has reached TikTok yet.
    access_expires = expiry(data, "access_token_expire_in")
    refresh_expires = expiry(data, "refresh_token_expire_in")
    conn.execute(
        "update tiktok_connections set access_token_enc = %s, refresh_token_enc = %s, "
        "access_expires_at = %s, refresh_expires_at = %s, refresh_attempted_at = %s, "
        "refresh_succeeded_at = %s, refresh_failure_code = null, refresh_failure_reason = null "
        "where shop_id = %s",
        (_encrypt(data["access_token"]), _encrypt(data.get("refresh_token") or ""),
         access_expires, refresh_expires, now, now, str(shop_id)))
    conn.execute("update shops set connection_status = 'connected' "
                 "where id = %s and connection_status = 'needs_reconnect'", (str(shop_id),))
    return "refreshed"


def client_for(conn, shop_id: UUID | str, transport: Transport = http_transport) -> Client:
    """A client carrying the shop's decrypted token and cipher, read inside its tenant."""
    row = conn.execute(
        "select access_token_enc, shop_cipher_enc from tiktok_connections "
        "where shop_id = %s and revoked_at is null", (str(shop_id),)).fetchone()
    if row is None:
        raise TikTokError("no_connection", "The shop has no live connection.")
    return Client(access_token=decrypt(row[0]),
                  shop_cipher=decrypt(row[1]) if row[1] else None, transport=transport)
