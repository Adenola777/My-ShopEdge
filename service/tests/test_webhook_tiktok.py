"""The TikTok webhook receiver, verified without a database, credentials or the network.

    python3 tests/test_webhook_tiktok.py

What this proves: the signature algorithm is TikTok's (HMAC-SHA256 of the app key followed by
the raw body, keyed by the app secret, lowercase hex), a bad or missing signature is refused
with 401, a verified event is acknowledged with 200 and handed to the background processor
once, a redelivery is not processed a second time, and an event for an unknown shop is
acknowledged and ignored. The store and the real sync run against the database and TikTok, so
they are checked separately, the way the rest of the TikTok code is.
"""

import hashlib
import hmac
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NEON_AUTH_JWKS_URL", "http://127.0.0.1:1/jwks.json")
os.environ.setdefault("NEON_AUTH_AUDIENCE", "test")
os.environ.setdefault("NEON_AUTH_ISSUER", "https://test.invalid")

from fastapi.testclient import TestClient

from app import tiktok_webhooks as wh
from app.main import app

APP_KEY = "test_app_key"
APP_SECRET = "test_app_secret"

failures = []


def check(name, condition):
    print(f"  {'ok  ' if condition else 'FAIL'} {name}")
    if not condition:
        failures.append(name)


def sign(raw: bytes) -> str:
    return hmac.new(APP_SECRET.encode(), APP_KEY.encode() + raw, hashlib.sha256).hexdigest()


print("tiktok webhook receiver")

# --- the pure pieces ---------------------------------------------------------------------
raw = b'{"type":"ORDER_STATUS_CHANGE","shop_id":"74949","tts_notification_id":"n1"}'
check("signature matches an independent HMAC", wh.webhook_signature(APP_KEY, APP_SECRET, raw) == sign(raw))
check("signature_ok accepts the right signature", wh.signature_ok(sign(raw), APP_KEY, APP_SECRET, raw))
check("signature_ok accepts an upper-case header", wh.signature_ok(sign(raw).upper(), APP_KEY, APP_SECRET, raw))
check("signature_ok rejects a wrong signature", not wh.signature_ok("deadbeef", APP_KEY, APP_SECRET, raw))
check("signature_ok rejects a missing header", not wh.signature_ok(None, APP_KEY, APP_SECRET, raw))
check("signature_ok rejects a body that was changed", not wh.signature_ok(sign(raw), APP_KEY, APP_SECRET, raw + b" "))

check("classify deauthorisation", wh.classify("SELLER_DEAUTHORIZATION") == "deauthorization")
check("classify expiry", wh.classify("UPCOMING_AUTHORIZATION_EXPIRATION") == "authorization_expiring")
check("classify order", wh.classify("ORDER_STATUS_CHANGE") == "sync")
check("classify return", wh.classify("RETURN_STATUS_CHANGE") == "sync")
check("classify product", wh.classify("PRODUCT_STATUS_CHANGE") == "sync")
check("classify unknown", wh.classify("SOMETHING_ELSE") == "other")

p = {"type": "ORDER", "shop_id": "74949", "tts_notification_id": "n1"}
check("event type read", wh._event_type(p) == "ORDER")
check("shop id read", wh._shop_tiktok_id(p) == "74949")
check("notification id read", wh._notification_id(p) == "n1")
check("shop id read from data", wh._shop_tiktok_id({"data": {"shop_id": "55"}}) == "55")

# --- the endpoint, with the store and processor stubbed ----------------------------------
os.environ["TIKTOK_APP_KEY"] = APP_KEY
os.environ["TIKTOK_APP_SECRET"] = APP_SECRET

seen_keys = set()
processed = []
marked = []


def fake_claim(dedupe_key, notification_id, event_type, shop_tiktok_id, payload):
    is_new = dedupe_key not in seen_keys
    seen_keys.add(dedupe_key)
    # A known shop resolves; the sentinel id "unknown" does not.
    if shop_tiktok_id == "unknown":
        return (is_new, None, None)
    return (is_new, "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222")


wh.claim = fake_claim
wh.process_event = lambda *a, **k: processed.append(a)
wh.mark = lambda key, status, note: marked.append((key, status))

client = TestClient(app)

body = json.dumps({"type": "ORDER_STATUS_CHANGE", "shop_id": "74949", "tts_notification_id": "n-100"}).encode()
r = client.post("/v1/webhooks/tiktok", content=body, headers={"Authorization": sign(body)})
check("verified event is acknowledged 200", r.status_code == 200)
check("verified event body is empty", r.content == b"")
check("verified event is processed once", len(processed) == 1)

# A redelivery of the same notification is acknowledged but not processed again.
r = client.post("/v1/webhooks/tiktok", content=body, headers={"Authorization": sign(body)})
check("redelivery is acknowledged 200", r.status_code == 200)
check("redelivery is not processed again", len(processed) == 1)

# A bad signature is refused with 401 and never processed.
r = client.post("/v1/webhooks/tiktok", content=body, headers={"Authorization": "wrong"})
check("bad signature is 401", r.status_code == 401)
check("bad signature is not processed", len(processed) == 1)

# An event for a shop this installation does not hold is acknowledged and ignored.
unknown = json.dumps({"type": "ORDER", "shop_id": "unknown", "tts_notification_id": "n-200"}).encode()
r = client.post("/v1/webhooks/tiktok", content=unknown, headers={"Authorization": sign(unknown)})
check("unknown shop is acknowledged 200", r.status_code == 200)
check("unknown shop is not processed", len(processed) == 1)
check("unknown shop is marked ignored", ("n-200", "ignored") in marked)

# With the app secret unset the receiver cannot verify, so it answers 503 and does nothing.
del os.environ["TIKTOK_APP_SECRET"]
r = client.post("/v1/webhooks/tiktok", content=body, headers={"Authorization": sign(body)})
check("unconfigured receiver is 503", r.status_code == 503)
os.environ["TIKTOK_APP_SECRET"] = APP_SECRET

print(f"\n{'all webhook checks pass' if not failures else 'WEBHOOK CHECKS FAILED: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
