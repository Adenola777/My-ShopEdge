"""Checks the notice emails (NTF-2, A16.3, A5.7) against a stand-in for Resend. 10 October 2026.

    createdb mse_mail
    DATABASE_URL=... python3 service/scripts/migrate.py
    DATABASE_URL=... python3 testdata/notice_email_check.py

It needs a database built from empty by `migrate.py` whose tables belong to `mse_migrator`, as
they do on Neon, so that the SECURITY DEFINER functions can read them. A local build run as a
superuser leaves the tables to that superuser; hand them over first with
`alter table ... owner to mse_migrator` for each table in `public`. Rows are written as the
connecting role and read back as the service reads them, through `db.tenant()` as `mse_app`
under row level security. Nothing reaches Resend or TikTok: every send goes to `Fake` below,
and the refresh refusal to a stand-in. Drop the database afterwards.

What it checks:
- With RESEND_API_KEY unset, the sweep sends nothing and leaves every notice pending.
- Each of the five emailed types is sent once, to the account's email, from the default sender,
  with the notice's own title as the subject, the Bearer key, and `notice-<id>` as the
  idempotency key; the notice records `sent`, the time, one attempt and Resend's id.
- A second sweep sends nothing.
- An in-app-only type, an opted-out account, a closing account, a notice marked done, and a
  notice four days old are each marked `not_emailed` with the reason, and none is sent.
- A refusal is kept pending and counted, and the third refusal marks the notice `failed`.
- One account's sweep never reads or changes another account's notices.
- getMe serves `email_notices`, and PATCH /me switches it off, after which nothing is sent.
- A TikTok deauthorisation writes one `connection_revoked` notice and emails it at once.
- A refresh refused after the access token lapsed writes one `connection_lapsed` notice, and a
  second refusal of the same token adds none.

**Run on 10 October 2026** against a database built from empty by `migrate.py`: 35 passed,
0 failed. `tiktok_sync_check.py` was run again the same day on a fresh database, because the
token refresh changed, and passed 45 of 45.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tiktok_sync_check  # noqa: E402,F401  sets the TikTok variables and the path

import psycopg  # noqa: E402

from app import db, mailer, notice_email, tiktok_webhooks  # noqa: E402
from app.connections import _encrypt  # noqa: E402
from app.tiktok_api import refresh_connection  # noqa: E402

ok = bad = 0
UTC = timezone.utc
NOW = datetime.now(UTC)


def check(cond, what):
    global ok, bad
    print(("PASS " if cond else "FAIL ") + what)
    ok += bool(cond)
    bad += not cond


class Fake:
    """Stands in for Resend. Answers 200 with an id, or refuses with `refuse` as the status."""

    def __init__(self, refuse=None):
        self.sent = []
        self.refuse = refuse

    def __call__(self, url, headers, payload):
        self.sent.append((url, headers, payload))
        if self.refuse:
            return self.refuse, {"message": "The domain is not verified."}
        return 200, {"id": f"re_{len(self.sent)}"}


def new_account(conn, n, status="active"):
    return conn.execute(
        "insert into accounts (email, auth_subject, display_name, status) values (%s, %s, 'Mail', "
        "%s) returning id", (f"mail-{n}@example.test", f"stack|mail-{n}", status)).fetchone()[0]


def new_shop(conn, account, n):
    return conn.execute(
        "insert into shops (account_id, tiktok_shop_id, shop_name, region, seller_type, currency, "
        "connection_status) values (%s, %s, %s, 'GB', 'LOCAL', 'GBP', 'connected') returning id",
        (account, f"mail-shop-{n}", f"Mail shop {n}")).fetchone()[0]


def notice(conn, account, shop, type_, key, created=None, status="unread", body="Body text."):
    return conn.execute(
        "insert into notifications (account_id, shop_id, type, severity, title, body, status, "
        "dedupe_key, created_at) values (%s, %s, %s, 'warning', %s, %s, %s, %s, %s) returning id",
        (account, shop, type_, f"Title of {key}", body, status, key, created or NOW)).fetchone()[0]


def state(url, notice_id):
    with psycopg.connect(url) as conn:
        return conn.execute(
            "select email_status, email_attempts, emailed_at, email_note from notifications "
            "where id = %s", (notice_id,)).fetchone()


def main():
    url = os.environ["DATABASE_URL"]
    os.environ.pop("RESEND_API_KEY", None)
    os.environ.pop("EMAIL_FROM", None)
    with psycopg.connect(url) as conn:
        a = new_account(conn, 1)
        shop_a = new_shop(conn, a, 1)
        b = new_account(conn, 2)
        shop_b = new_shop(conn, b, 2)
        emailed = {t: notice(conn, a, shop_a if t != "order_limit_passed" else None, t, f"a-{t}")
                   for t in sorted(notice_email.EMAILED_TYPES)}
        in_app = notice(conn, a, shop_a, "low_stock", "a-low")
        done = notice(conn, a, shop_a, "reconnect_needed", "a-done", status="done")
        old = notice(conn, a, shop_a, "reconnect_needed", "a-old", created=NOW - timedelta(days=4))
        b_notice = notice(conn, b, shop_b, "order_limit_passed", "b-limit")

    # --- unconfigured ------------------------------------------------------------------------
    fake = Fake()
    check(notice_email.send_due(transport=fake) == {"state": "unconfigured"} and not fake.sent,
          "without RESEND_API_KEY nothing is sent")
    check(state(url, emailed["reconnect_needed"])[0] == "pending", "and the notice stays pending")

    # --- one account, configured -------------------------------------------------------------
    os.environ["RESEND_API_KEY"] = "re_test_not_a_real_key"
    counts = notice_email.send_for_account(a, NOW, fake)
    check(counts == {"sent": 5, "not_emailed": 3, "failed": 0, "retry": 0},
          f"account A: five sent, three not emailed ({counts})")
    check(state(url, b_notice)[0] == "pending", "account B's notice is untouched by A's sweep")
    to = {tuple(p["to"]) for _, _, p in fake.sent}
    check(to == {("mail-1@example.test",)}, "every email goes to account A's address")
    url0, headers0, payload0 = fake.sent[0]
    check(url0 == "https://api.resend.com/emails", "sent to Resend's emails endpoint")
    check(headers0["Authorization"] == "Bearer re_test_not_a_real_key", "with the Bearer key")
    check(payload0["from"] == mailer.DEFAULT_FROM, "from the default sender")
    keys = {h["Idempotency-Key"] for _, h, _ in fake.sent}
    check(keys == {f"notice-{i}" for i in emailed.values()}, "idempotency key is notice-<id>")
    subjects = {p["subject"] for _, _, p in fake.sent}
    check(subjects == {f"Title of a-{t}" for t in emailed}, "subject is the notice's title")
    limit_text = next(p["text"] for _, _, p in fake.sent if p["subject"] == "Title of a-order_limit_passed")
    shop_text = next(p["text"] for _, _, p in fake.sent if p["subject"] == "Title of a-reconnect_needed")
    check("/shops\n" in limit_text + "\n" and f"/shops/{shop_a}/notifications" in shop_text,
          "the link goes to the shop's notices, or to the shop list for an account notice")
    check("Body text." in shop_text and "switch them off in Settings" in shop_text,
          "the text carries the notice's body and how to switch email off")
    s = state(url, emailed["scheduled_export_ready"])
    check(s[0] == "sent" and s[1] == 1 and s[2] is not None and s[3].startswith("re_"),
          f"a sent notice records sent, one attempt, the time and Resend's id ({s})")
    check(state(url, in_app)[:2] == ("not_emailed", 0)
          and "app only" in state(url, in_app)[3], "low stock is not emailed, with the reason")
    check("marked the notice done" in state(url, done)[3], "a notice already done is not emailed")
    check("three days old" in state(url, old)[3], "a notice four days old is not emailed")

    before = len(fake.sent)
    notice_email.send_for_account(a, NOW, fake)
    check(len(fake.sent) == before, "a second sweep sends nothing")

    # --- the daily sweep across accounts -----------------------------------------------------
    summary = notice_email.send_due(NOW, fake)
    check(summary["accounts"] == 1 and summary["sent"] == 1 and state(url, b_notice)[0] == "sent",
          f"send_due finds account B through notices_due_for_email ({summary})")

    # --- opted out, closing ------------------------------------------------------------------
    with psycopg.connect(url) as conn:
        c = new_account(conn, 3)
        conn.execute("update accounts set email_notices = false where id = %s", (c,))
        c_notice = notice(conn, c, None, "order_limit_passed", "c-limit")
        d = new_account(conn, 4, status="deleted")
        d_notice = notice(conn, d, None, "order_limit_passed", "d-limit")
    before = len(fake.sent)
    notice_email.send_due(NOW, fake)
    check(len(fake.sent) == before, "an opted-out account and a closing account get no email")
    check("switched email notices off" in state(url, c_notice)[3], "opted out, with the reason")
    check("not active" in state(url, d_notice)[3], "closing, with the reason")

    # --- refusals ----------------------------------------------------------------------------
    with psycopg.connect(url) as conn:
        e = new_account(conn, 5)
        e_notice = notice(conn, e, None, "order_limit_passed", "e-limit")
    refusing = Fake(refuse=403)
    notice_email.send_for_account(e, NOW, refusing)
    s = state(url, e_notice)
    check(s[0] == "pending" and s[1] == 1 and s[3].startswith("403"),
          f"a refusal keeps the notice pending with Resend's answer ({s})")
    notice_email.send_for_account(e, NOW, refusing)
    counts = notice_email.send_for_account(e, NOW, refusing)
    s = state(url, e_notice)
    check(s[0] == "failed" and s[1] == 3 and counts["failed"] == 1,
          f"the third refusal marks it failed ({s})")
    check(len(refusing.sent) == 3, "and nothing is tried a fourth time")

    # --- getMe and PATCH /me -----------------------------------------------------------------
    from fastapi.testclient import TestClient

    from app.auth import Account, require_account, require_signed_in
    from app.main import app

    with psycopg.connect(url) as conn:
        f = new_account(conn, 6)
        f_shop = new_shop(conn, f, 6)
    who = Account(id=UUID(str(f)), email="mail-6@example.test", name="Mail", subject="stack|mail-6")
    app.dependency_overrides[require_account] = lambda: who
    app.dependency_overrides[require_signed_in] = lambda: who
    client = TestClient(app)
    r = client.get("/v1/me")
    check(r.status_code == 200 and r.json().get("email_notices") is True,
          f"getMe serves email_notices true by default ({r.status_code})")
    r = client.patch("/v1/me", json={"email_notices": False})
    check(r.status_code == 200 and r.json().get("email_notices") is False,
          f"PATCH /me switches it off ({r.status_code} {r.text[:200]})")
    r = client.patch("/v1/me", json={"email_notices": False, "email": "x@example.test"})
    check(r.status_code == 422, f"PATCH /me refuses any other field ({r.status_code})")
    check(client.get("/v1/me").json().get("email_notices") is False, "getMe then reads false")
    with psycopg.connect(url) as conn:
        f_notice = notice(conn, f, f_shop, "reconnect_needed", "f-reconnect")
    before = len(fake.sent)
    notice_email.send_for_account(f, NOW, fake)
    check(len(fake.sent) == before and state(url, f_notice)[0] == "not_emailed",
          "after switching off, nothing is sent")
    r = client.patch("/v1/me", json={"email_notices": True})
    check(r.json().get("email_notices") is True, "PATCH /me switches it back on")

    # --- the webhook's deauthorisation -------------------------------------------------------
    with psycopg.connect(url) as conn:
        g = new_account(conn, 7)
        g_shop = new_shop(conn, g, 7)
    webhook_fake = Fake()
    real_transport = mailer.http_transport
    mailer.http_transport = webhook_fake
    try:
        for _ in range(2):
            tiktok_webhooks.process_event("dedupe-deauth-1", str(g), str(g_shop),
                                          "SELLER_DEAUTHORIZATION")
    finally:
        mailer.http_transport = real_transport
    with psycopg.connect(url) as conn:
        rows = conn.execute(
            "select type, severity, email_status from notifications where account_id = %s",
            (g,)).fetchall()
        status = conn.execute("select connection_status from shops where id = %s",
                              (g_shop,)).fetchone()[0]
    check(status == "disconnected", "the deauthorisation disconnects the shop, as before")
    check(rows == [("connection_revoked", "critical", "sent")],
          f"it writes one critical connection_revoked notice and emails it at once ({rows})")
    check(len(webhook_fake.sent) == 1, "one email, though the event was processed twice")

    # --- a refresh refused after the token lapsed --------------------------------------------
    with psycopg.connect(url) as conn:
        h = new_account(conn, 8)
        h_shop = new_shop(conn, h, 8)
        conn.execute(
            "insert into tiktok_connections (shop_id, access_token_enc, refresh_token_enc, "
            "shop_cipher_enc, access_expires_at, refresh_expires_at, scopes) values (%s, %s, %s, "
            "%s, %s, %s, '{seller.order.info}')",
            (h_shop, _encrypt("access"), _encrypt("refresh"), _encrypt("cipher"),
             NOW - timedelta(hours=1), NOW + timedelta(days=300)))

    def refuse(method, url_, params, headers, body):
        return {"code": 36004004, "message": "refresh token is invalid"}

    for _ in range(2):
        with db.tenant(h) as conn:
            result = refresh_connection(conn, h_shop, NOW, refuse)
    with psycopg.connect(url) as conn:
        rows = conn.execute("select type, severity from notifications where account_id = %s",
                            (h,)).fetchall()
        status = conn.execute("select connection_status from shops where id = %s",
                              (h_shop,)).fetchone()[0]
    check(result == "failed" and status == "needs_reconnect",
          "a refused refresh of a lapsed token marks the shop needs_reconnect, as before")
    check(rows == [("connection_lapsed", "critical")],
          f"it writes one critical connection_lapsed notice, and none the second time ({rows})")

    print(f"\n{ok} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
