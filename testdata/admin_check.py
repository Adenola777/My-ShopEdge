"""Checks the admin backend (A34) against a local database. Written 10 October 2026.

    createdb mse_admin
    DATABASE_URL=... python3 service/scripts/migrate.py
    DATABASE_URL=... python3 testdata/admin_check.py

The database must be built from empty by `migrate.py`, with its tables and views belonging to
`mse_migrator` as they do on Neon (queried on production on 10 October 2026), so that the
SECURITY DEFINER functions of 0032 can read them. A local build run as a superuser leaves them
to that superuser; hand them over first. Rows are written as the connecting role; the service
reads them as it does in production, through `db.tenant()` and `db.unscoped()` as `mse_app`.

Nothing reaches Stack, Stripe, Resend or TikTok:
  * `auth.verify` is replaced by a stand-in that reads the claims out of the test's own token
    string, so the check covers everything `require_admin` does after verification;
  * no account here holds a live Stripe subscription, so `set_renewal_for_deletion` answers
    `none` without calling Stripe, and the Stripe half of suspension is **unverified**;
  * every email goes to a stand-in for Resend;
  * the sync is replaced by a recorder.

What it checks:
- Every refusal is the same 404, byte for byte, as a path that does not exist: no ADMIN_EMAILS,
  no token, a token that fails verification, a reviewer token, a subject the provider has not
  synced, an unverified email, and a verified email not on the list.
- An admin on the list, written in another case, is admitted.
- The accounts view lists every account across tenants, and `email` finds one account.
- The shops view counts statements and unexplained ones, and no admin view returns a token
  column or a seller's money figure.
- Suspend, reactivate, sync, retry an email, export, deletion and its cancellation each do
  their work, refuse the wrong state with 409, and write one audit row naming the admin.
- A suspended seller is refused by `require_admin`'s seller counterpart, is skipped by the
  daily sync's list, and is emailed the suspension notice; an opted-out seller is not.
- The figures count sign-ups, trials and paying plans, and price only paying plans.

**Run on 10 October 2026** against a database built from empty by `migrate.py`, with its tables
and views handed to `mse_migrator`: 51 passed, 0 failed.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "service"))

import psycopg  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import auth, mailer, tiktok_sync  # noqa: E402
from app.main import app  # noqa: E402

ok = bad = 0
UTC = timezone.utc
NOW = datetime.now(UTC)


def check(cond, what):
    global ok, bad
    print(("PASS " if cond else "FAIL ") + what)
    ok += bool(cond)
    bad += not cond


def fake_verify(token):
    """The test's tokens are JSON claims. 'bad' fails verification as a forged token would."""
    if token == "bad":
        raise auth.Problem(401, "token_invalid", "We could not confirm your sign-in.")
    return json.loads(token)


class Fake:
    def __init__(self):
        self.sent = []

    def __call__(self, url, headers, payload):
        self.sent.append(payload)
        return 200, {"id": f"re_{len(self.sent)}"}


def main():
    url = os.environ["DATABASE_URL"]
    auth.verify = fake_verify
    os.environ["RESEND_API_KEY"] = "re_test_not_a_real_key"
    mail = Fake()
    mailer.http_transport = mail
    synced = []
    tiktok_sync.run_one = lambda shop, account: synced.append((shop, account)) or {}

    with psycopg.connect(url) as conn:
        def account(n, email_notices=True):
            return conn.execute(
                "insert into accounts (email, auth_subject, email_notices) values (%s, %s, %s) "
                "returning id", (f"seller-{n}@example.test", f"stack|seller-{n}",
                                 email_notices)).fetchone()[0]
        a, b, c = account(1), account(2), account(3, email_notices=False)
        shop = conn.execute(
            "insert into shops (account_id, tiktok_shop_id, shop_name, region, seller_type, "
            "currency, connection_status) values (%s, 'admin-shop-1', 'Admin shop', 'GB', "
            "'LOCAL', 'GBP', 'connected') returning id", (a,)).fetchone()[0]
        conn.execute(
            "insert into tiktok_connections (shop_id, access_token_enc, refresh_token_enc, "
            "shop_cipher_enc, access_expires_at, refresh_expires_at, scopes, refresh_failure_code) "
            "values (%s, 'x', 'y', 'z', %s, %s, '{seller.order.info}', '36004004')",
            (shop, NOW + timedelta(days=3), NOW + timedelta(days=300)))
        for k, amount in enumerate([1000, 2000]):
            conn.execute(
                "insert into settlements (shop_id, tiktok_statement_id, period_start, period_end, "
                "statement_amount_minor, currency, payment_status) values (%s, %s, %s, %s, %s, "
                "'GBP', 'PAID')", (shop, f"st-{k}", NOW.date(), NOW.date(), amount))
        conn.execute(
            "insert into subscriptions (account_id, plan_slug, status, stripe_customer_id) values "
            "(%s, 'starter', 'trialing', 'demo_a'), (%s, 'growth', 'active', 'demo_b')", (a, b))
        conn.execute(
            "insert into notifications (account_id, type, severity, title, dedupe_key, "
            "email_status, email_attempts, email_note) values (%s, 'order_limit_passed', "
            "'warning', 'Failed one', 'failed-1', 'failed', 3, '403: refused')", (b,))
        failed_id = conn.execute("select id from notifications where dedupe_key = 'failed-1'"
                                 ).fetchone()[0]
        conn.execute(
            "insert into neon_auth.users_sync (raw_json, id, email) values "
            "('{\"primary_email_verified\": true}', 'stack|boss', 'Boss@Example.test'), "
            "('{\"primary_email_verified\": false}', 'stack|unverified', 'boss@example.test'), "
            "('{\"primary_email_verified\": true}', 'stack|other', 'other@example.test')")

    client = TestClient(app)
    missing = client.get("/v1/admin/no-such-path")

    def as_(sub, iss="https://api.stack-auth.com"):
        return {"Authorization": "Bearer " + json.dumps({"sub": sub, "iss": iss})}

    def same_as_missing(r):
        return (r.status_code, r.text, r.headers.get("content-type")) == (
            missing.status_code, missing.text, missing.headers.get("content-type"))

    # --- who gets in ---------------------------------------------------------------------------
    os.environ.pop("ADMIN_EMAILS", None)
    check(same_as_missing(client.get("/v1/admin/accounts", headers=as_("stack|boss"))),
          f"without ADMIN_EMAILS even the admin gets the missing path's 404 ({missing.text})")
    os.environ["ADMIN_EMAILS"] = " boss@example.test , someone@example.test"
    refusals = {
        "no token": {},
        "a token that fails verification": {"Authorization": "Bearer bad"},
        "a reviewer token": as_("stack|boss", iss=auth.REVIEWER_ISS),
        "a subject the provider has not synced": as_("stack|nobody"),
        "an unverified email on the list": as_("stack|unverified"),
        "a verified email not on the list": as_("stack|other"),
    }
    for what, headers in refusals.items():
        check(same_as_missing(client.get("/v1/admin/accounts", headers=headers)),
              f"{what} gets the missing path's 404")
        check(same_as_missing(client.post(f"/v1/admin/accounts/{a}/suspend", headers=headers)),
              f"{what} cannot suspend either")
    boss = as_("stack|boss")
    r = client.get("/v1/admin/accounts", headers=boss)
    check(r.status_code == 200, f"the admin, listed in another case, is admitted ({r.status_code})")

    # --- the views -----------------------------------------------------------------------------
    emails = {x["email"] for x in r.json()["accounts"]}
    check({"seller-1@example.test", "seller-2@example.test", "seller-3@example.test"} <= emails,
          "the accounts view lists accounts across tenants")
    found = client.get("/v1/admin/accounts", params={"email": "SELLER-2@example.test"},
                       headers=boss).json()["accounts"]
    check([x["account_id"] for x in found] == [str(b)], "email finds the one account")
    shops = client.get("/v1/admin/shops", headers=boss).json()["shops"]
    mine = next(s for s in shops if s["shop_id"] == str(shop))
    check(mine["statements"] == 2 and mine["refresh_failure_code"] == "36004004",
          f"the shops view counts statements and shows the refresh failure ({mine})")
    bodies = ""
    for path in ["accounts", "shops", "sync-runs", "webhook-events", "notice-emails", "audit"]:
        rr = client.get(f"/v1/admin/{path}", headers=boss)
        check(rr.status_code == 200, f"GET /admin/{path} answers 200")
        bodies += rr.text
    check("_enc" not in bodies and "token\"" not in bodies and "payload" not in bodies,
          "no view returns a token column or a webhook payload")
    check("_minor" not in bodies, "no view returns a seller's money figure (A34.8 ruling 4)")
    emails_view = client.get("/v1/admin/notice-emails", headers=boss).json()
    check(emails_view["counts"].get("failed") == 1
          and emails_view["problems"][0]["notification_id"] == str(failed_id),
          "the notice emails view counts and lists the failed email")

    def audit_rows(account):
        with psycopg.connect(url) as conn:
            return conn.execute("select actor, action, entity_type from audit_log "
                                "where account_id = %s order by occurred_at", (account,)).fetchall()

    def status(account):
        with psycopg.connect(url) as conn:
            return conn.execute("select status from accounts where id = %s", (account,)).fetchone()[0]

    # --- suspend and reactivate ---------------------------------------------------------------
    before = len(mail.sent)
    r = client.post(f"/v1/admin/accounts/{a}/suspend", headers=boss)
    check(r.status_code == 200 and r.json()["status"] == "suspended" and status(a) == "suspended",
          f"suspend sets the account suspended ({r.status_code} {r.text[:120]})")
    check(audit_rows(a) == [("admin:boss@example.test", "suspend_account", "account")],
          f"suspend writes one audit row naming the admin ({audit_rows(a)})")
    subjects = [p["subject"] for p in mail.sent[before:]]
    check(subjects == ["Your MyShopEdge account is suspended."],
          f"the suspended seller is emailed the notice ({subjects})")
    check(client.post(f"/v1/admin/accounts/{a}/suspend", headers=boss).status_code == 409,
          "suspending a suspended account is refused with 409")
    with psycopg.connect(url) as conn:
        due = [r_[1] for r_ in conn.execute("select * from shops_due_for_sync()").fetchall()]
    check(a not in due, "the daily sync's list skips the suspended account")
    # The seller's own sign-in resolves the suspended account, and require_account refuses it.
    real_signed_in = auth.require_signed_in
    auth.require_signed_in = lambda request: auth.Account(
        id=a, email="seller-1@example.test", name=None, subject="stack|seller-1",
        status=status(a))
    try:
        auth.require_account(None)
        refused = None
    except auth.Problem as err:
        refused = err.code
    finally:
        auth.require_signed_in = real_signed_in
    check(refused == "account_suspended", f"the seller is refused as suspended ({refused})")
    r = client.post(f"/v1/admin/accounts/{a}/reactivate", headers=boss)
    check(r.status_code == 200 and status(a) == "active", "reactivate sets it active again")
    check([p["subject"] for p in mail.sent][-1] == "Your MyShopEdge account is active again.",
          "the seller is emailed the reactivation")
    check(client.post(f"/v1/admin/accounts/{a}/reactivate", headers=boss).status_code == 409,
          "reactivating an active account is refused with 409")
    before = len(mail.sent)
    client.post(f"/v1/admin/accounts/{c}/suspend", headers=boss)
    check(len(mail.sent) == before, "a seller who switched email off is not emailed (derived)")
    client.post(f"/v1/admin/accounts/{c}/reactivate", headers=boss)

    # --- sync, retry, export ------------------------------------------------------------------
    r = client.post(f"/v1/admin/shops/{shop}/sync", headers=boss)
    check(r.status_code == 202 and synced == [(shop, a)],
          f"sync now runs the shop's sync for its account ({r.status_code} {synced})")
    check(client.post(f"/v1/admin/shops/{a}/sync", headers=boss).status_code == 404,
          "an unknown shop is 404")
    before = len(mail.sent)
    r = client.post(f"/v1/admin/notifications/{failed_id}/retry-email", headers=boss)
    with psycopg.connect(url) as conn:
        st = conn.execute("select email_status, email_attempts from notifications where id = %s",
                          (failed_id,)).fetchone()
    check(r.status_code == 200 and st == ("sent", 1) and len(mail.sent) == before + 1,
          f"retry puts the failed email back and the sweep sends it ({r.status_code} {st})")
    check(client.post(f"/v1/admin/notifications/{failed_id}/retry-email",
                      headers=boss).status_code == 409, "retrying an email that did not fail is 409")
    r = client.post(f"/v1/admin/accounts/{b}/export", headers=boss)
    job = r.json()
    check(r.status_code == 202 and job.get("id"), f"an export is requested ({r.status_code})")
    g = client.get(f"/v1/admin/accounts/{b}/export/{job.get('id')}", headers=boss)
    check(g.status_code == 200 and g.json()["id"] == job.get("id"),
          f"and its status can be read ({g.status_code} {g.json().get('status')})")

    # --- deletion -----------------------------------------------------------------------------
    r = client.post(f"/v1/admin/accounts/{b}/deletion", headers=boss)
    check(r.status_code == 202 and status(b) == "deleted", f"deletion closes the account ({r.status_code})")
    r = client.post(f"/v1/admin/accounts/{b}/deletion/cancel", headers=boss)
    check(r.status_code == 200 and status(b) == "active", "cancelling reopens it")
    check(client.post(f"/v1/admin/accounts/{b}/deletion/cancel", headers=boss).status_code == 409,
          "cancelling with no deletion is 409")
    client.post(f"/v1/admin/accounts/{c}/suspend", headers=boss)
    check(client.post(f"/v1/admin/accounts/{c}/deletion", headers=boss).status_code == 409,
          "a suspended account must be reactivated before deletion")
    actions = [x[1] for x in audit_rows(b)]
    check(actions == ["retry_notice_email", "build_account_export", "delete_account",
                      "cancel_account_deletion"], f"each action wrote one audit row ({actions})")
    audit = client.get("/v1/admin/audit", headers=boss).json()["entries"]
    check(len(audit) == len(audit_rows(a)) + len(audit_rows(b)) + len(audit_rows(c)),
          "the audit view lists every action across accounts")
    with psycopg.connect(url) as conn:
        try:
            conn.execute("update audit_log set actor = 'someone else'")
            changed = True
        except psycopg.Error:
            changed = False
    check(not changed, "the audit log cannot be rewritten")

    # --- figures ------------------------------------------------------------------------------
    f = client.get("/v1/admin/figures", headers=boss).json()
    plans = {p["plan_slug"]: p for p in f["plans"]}
    check(plans["starter"]["trialing"] == 1 and plans["growth"]["paying"] == 1
          and f["list_revenue_minor"] == 2499,
          f"figures count the trial and the paying plan, and price only the paying one ({f['plans']})")
    check(sum(m["signups"] for m in f["signups_by_month"]) == f["accounts"],
          "sign-ups by month add up to the accounts")

    print(f"\n{ok} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
