"""The TikTok client and the mapping helpers, without a database or the network.

    python3 tests/test_tiktok_client.py

Written 29 September 2026 for part 1 of the batch. The full sync runs against a database in
testdata/tiktok_sync_check.py; this covers what can go wrong before a database is reached.
"""

import base64
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["TIKTOK_APP_KEY"] = "test-key"
os.environ["TIKTOK_APP_SECRET"] = "test-secret"
os.environ["TIKTOK_TOKEN_KEY"] = base64.b64encode(secrets.token_bytes(32)).decode()

from app import tiktok_api  # noqa: E402
from app import connections  # noqa: E402
from app.connections import _encrypt, _sign  # noqa: E402
from app.tiktok_sync import allocate, pence  # noqa: E402

failures = 0


def check(name, fn):
    global failures
    try:
        fn()
        print(f"  PASS  {name}")
    except Exception as err:  # noqa: BLE001
        failures += 1
        print(f"  FAIL  {name}: {type(err).__name__}: {err}")


def _assert(cond, detail=""):
    if not cond:
        raise AssertionError(detail)


class Recorder:
    def __init__(self, answers):
        self.answers = list(answers)
        self.sent = []

    def __call__(self, method, url, params, headers, body):
        self.sent.append((method, url, dict(params), dict(headers), body))
        return self.answers.pop(0)


def ok(data):
    return {"code": 0, "message": "Success", "data": data}


print("tiktok client")


def refuses_wrong_sort_field():
    c = tiktok_api.Client("tok", "cipher", Recorder([]))
    for query in ({"sort_field": "create_time", "sort_order": "ASC"}, {"sort_order": "ASC"},
                  {"sort_field": "statement_time"}):
        try:
            c.call("GET", tiktok_api.STATEMENTS_PATH, query)
        except ValueError:
            continue
        raise AssertionError(f"{query} was sent")
    try:
        c.call("GET", "/finance/202501/statements/S1/statement_transactions",
               {"sort_field": "statement_time", "sort_order": "ASC"})
    except ValueError:
        return
    raise AssertionError("statement_transactions accepted statement_time")
check("a sort field TikTok would silently ignore is refused before sending (A19.4)", refuses_wrong_sort_field)


def signs_what_it_sends():
    r = Recorder([ok({"statements": []})])
    c = tiktok_api.Client("tok", "cipher", r)
    c.call("GET", tiktok_api.STATEMENTS_PATH, {"sort_field": "statement_time", "sort_order": "ASC",
                                                "statement_time_ge": "1"})
    method, url, params, headers, body = r.sent[0]
    _assert(url == "https://open-api.tiktokglobalshop.com/finance/202309/statements", url)
    _assert(headers["x-tts-access-token"] == "tok" and "access_token" not in params)
    _assert(params["shop_cipher"] == "cipher" and params["app_key"] == "test-key")
    _assert(len(params["timestamp"]) == 10, params["timestamp"])
    unsigned = {k: v for k, v in params.items() if k != "sign"}
    _assert(params["sign"] == _sign("/finance/202309/statements", unsigned, b"", "test-secret"))
check("a GET carries the token in the header, the cipher, a ten digit timestamp and its signature",
      signs_what_it_sends)


def signs_post_body():
    r = Recorder([ok({"orders": []})])
    c = tiktok_api.Client("tok", None, r)
    c.call("POST", tiktok_api.ORDER_SEARCH_PATH, {"sort_field": "update_time", "sort_order": "ASC"},
           {"update_time_ge": 5})
    _m, _u, params, _h, body = r.sent[0]
    _assert(body == b'{"update_time_ge":5}', body)
    unsigned = {k: v for k, v in params.items() if k != "sign"}
    _assert(params["sign"] == _sign(tiktok_api.ORDER_SEARCH_PATH, unsigned, body, "test-secret"))
    _assert("shop_cipher" not in params)
check("a POST signs the exact body it sends", signs_post_body)


def refusal_carries_code():
    c = tiktok_api.Client("tok", None, Recorder([{"code": 36009004, "message": "Invalid timestamp"}]))
    try:
        c.call("GET", tiktok_api.ORDER_DETAIL_PATH, {"ids": "1"})
    except tiktok_api.TikTokError as err:
        _assert(err.code == "36009004" and err.message == "Invalid timestamp")
        return
    raise AssertionError("a refusal was returned as data")
check("a refusal with HTTP 200 raises with TikTok's own code", refusal_carries_code)


def pages_follow_token():
    r = Recorder([ok({"statements": [1], "next_page_token": "t2"}),
                  ok({"statements": [2], "next_page_token": ""})])
    c = tiktok_api.Client("tok", None, r)
    got = [p["statements"] for p in c.pages("GET", tiktok_api.STATEMENTS_PATH,
                                             {"sort_field": "statement_time", "sort_order": "ASC"})]
    _assert(got == [[1], [2]], got)
    _assert(r.sent[0][2]["page_size"] == "100" and tiktok_api.PAGE_TOKEN_PARAM not in r.sent[0][2])
    _assert(r.sent[1][2][tiktok_api.PAGE_TOKEN_PARAM] == "t2")
check("a listing follows next_page_token to the end at 100 a page", pages_follow_token)


def returns_page_size():
    # TikTok refused 100 here on 29 September 2026: "allowed range (10 to 50)".
    r = Recorder([ok({"return_orders": [], "next_page_token": ""})])
    c = tiktok_api.Client("tok", "cipher", r)
    list(c.pages("POST", tiktok_api.RETURN_SEARCH_PATH, {"sort_field": "create_time", "sort_order": "ASC"}, {}))
    _assert(r.sent[0][2]["page_size"] == "50", r.sent[0][2])
check("the returns search asks for 50 a page, the most TikTok allows there", returns_page_size)


def pages_stop_loop():
    r = Recorder([ok({"next_page_token": "same"}), ok({"next_page_token": "same"})])
    c = tiktok_api.Client("tok", None, r)
    try:
        list(c.pages("GET", tiktok_api.STATEMENTS_PATH, {"sort_field": "statement_time", "sort_order": "ASC"}))
    except tiktok_api.TikTokError as err:
        _assert(err.code == "page_loop")
        return
    raise AssertionError("a repeated token was followed")
check("a page token handed back twice stops the listing", pages_stop_loop)


def refresh_window():
    now = datetime(2026, 9, 29, tzinfo=timezone.utc)
    _assert(not tiktok_api.refresh_due(now + timedelta(days=3), now))
    _assert(tiktok_api.refresh_due(now + timedelta(days=1, hours=23), now))
    _assert(tiktok_api.refresh_due(now - timedelta(hours=1), now))
    _assert(tiktok_api.refresh_due(None, now))
check("a refresh is due once fewer than two days are left", refresh_window)


def expiry_is_a_unix_time():
    # The first real authorisation, 29 September 2026, answered 1791309162 at 17:52:43 UTC.
    got = connections.expiry({"access_token_expire_in": 1791309162}, "access_token_expire_in")
    _assert(got == datetime(2026, 10, 6, 17, 52, 42, tzinfo=timezone.utc), got)
    _assert(connections.expiry({}, "access_token_expire_in") is None)
check("TikTok's expire_in fields are read as Unix times, not durations", expiry_is_a_unix_time)


def refresh_request():
    r = Recorder([ok({"access_token": "a2", "refresh_token": "r2", "access_token_expire_in": 604800})])
    data = tiktok_api.refresh_tokens("r1", r)
    method, url, params, _h, _b = r.sent[0]
    _assert(method == "GET" and url == "https://auth.tiktok-shops.com/api/v2/token/refresh", url)
    _assert(params == {"app_key": "test-key", "app_secret": "test-secret", "refresh_token": "r1",
                       "grant_type": "refresh_token"}, params)
    _assert(data["access_token"] == "a2")
    try:
        tiktok_api.refresh_tokens("r1", Recorder([{"code": 36004001, "message": "expired"}]))
    except tiktok_api.TikTokError as err:
        _assert(err.code == "36004001")
        return
    raise AssertionError("a refused refresh returned data")
check("the refresh sends A23.4's four parameters and raises TikTok's code on refusal", refresh_request)


def decrypt_round_trip():
    _assert(tiktok_api.decrypt(_encrypt("secret-token")) == "secret-token")
check("a stored token decrypts to what was stored", decrypt_round_trip)


def money_rules():
    _assert(pence("1.005") == 101 and pence("-33.49") == -3349 and pence("") == 0 and pence(None) == 0)
    try:
        pence("1", "IDR")
    except ValueError:
        pass
    else:
        raise AssertionError("an unverified currency was converted")
    for total, n in ((-100, 3), (101, 2), (7, 1), (0, 4), (-1, 5)):
        parts = allocate(total, [1] * n)
        _assert(sum(parts) == total and max(parts) - min(parts) <= 1, (total, parts))
check("money is Decimal, GBP only, and a split leaves no residual pence", money_rules)


def per_unit_rounding():
    from app.money import per_unit
    # The Curly Hair Brush in the demo year: 22 units. Floor division gave -273 for the
    # refund only because it rounds negatives away from zero; half up is symmetric.
    for amount, units, want in ((-6000, 22, -273), (34700, 22, 1577), (5, 2, 3), (-5, 2, -3),
                                (-4, 3, -1), (4, 3, 1), (100, 0, 100)):
        _assert(per_unit(amount, units) == want, (amount, units, per_unit(amount, units)))
check("one unit's share rounds half away from zero, the same for costs and sales", per_unit_rounding)


print("")
if failures:
    print(f"{failures} failure(s)")
    sys.exit(1)
print("every client case held")
