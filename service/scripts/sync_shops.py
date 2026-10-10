"""Refreshes and syncs every connected shop once. Part 1 of the batch of 29 September 2026.

    DATABASE_URL=... TIKTOK_APP_KEY=... TIKTOK_APP_SECRET=... TIKTOK_TOKEN_KEY=... \
        python3 scripts/sync_shops.py

It connects as the service does and runs as `mse_app`. It finds the shops through
`shops_due_for_sync()` from migration 0027, then for each one refreshes the access token if
fewer than two days are left (A23.4) and reads orders, returns and statements since its last
run. Running it twice in a row writes nothing new the second time.

**Never run against TikTok.** It has run only against the generated payloads through
`testdata/tiktok_sync_check.py`, on 29 September 2026, where all 36 checks passed on both
the two-month and the year datasets. Nothing schedules it yet. Migration 0027 is on no Neon
branch, and a Render cron job running it is the owner's to create.

Since 30 September 2026 each run also reads TikTok's stock count for every variant it has
read from an order, through Inventory Search, into `stock_positions` (A32), and applies
STK-8's absorption (A4.1).

Since 9 October 2026 each run also asks Neon whether the Data API is on for production
(`app.data_api_guard`). If it is on, the run fails after syncing, so the failure shows in the
job's history. Without `NEON_API_KEY` on the job it reports "not checked" and fails nothing.

Since 9 October 2026 each run then builds the scheduled exports due on today's London date
(`app.export_schedules.run_due`, MON-8). A schedule whose file cannot be stored because the R2
variables are absent is reported as not built, is not marked as run, and fails nothing. Before
migration 0030 is applied the schedules cannot be listed, and the run says so and fails
nothing. A scheduled export that fails for any other reason fails the run, so it shows in the
job's history.

Since 10 October 2026 each run then emails the notices NTF-2, A16.3 and A5.7 ask for, through
Resend (`app.notice_email.send_due`). Without `RESEND_API_KEY` on the job it reports "not sent"
and leaves every notice pending. Before migration 0031 is applied the notices cannot be listed,
and the run says so and fails nothing. A notice that Resend refuses for the third time fails
the run, so it shows in the job's history.

The secrets come from the environment and are never printed. The output names shops by
MyShopEdge id and gives TikTok's own error code and message when a call is refused.
"""

import json
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import data_api_guard, export_schedules, notice_email  # noqa: E402
from app.tiktok_sync import run_due  # noqa: E402


def scheduled_exports() -> bool:
    """Builds the scheduled exports due today and prints what happened. True if one failed."""
    try:
        runs = export_schedules.run_due()
    except psycopg.errors.UndefinedFunction:
        print("Scheduled exports were not run, because migration 0030 is not applied to this "
              "database.")
        return False
    except Exception as err:  # noqa: BLE001  the sync above has already been committed
        print(f"Scheduled exports could not be listed: {type(err).__name__}: {err}")
        return True
    print(json.dumps(runs, indent=2, default=str))
    built = sum(r["status"] == "built" for r in runs)
    again = sum(r["status"] == "already_run" for r in runs)
    unstored = sum(r["status"] == "storage_unconfigured" for r in runs)
    errors = sum(r["status"] == "error" for r in runs)
    print(f"{built} scheduled export(s) built, {again} already built today, {unstored} not built "
          f"because file storage is not configured, {errors} with an error.")
    return errors > 0


def notice_emails() -> bool:
    """Emails the notices due and prints what happened. True if one failed for good."""
    try:
        summary = notice_email.send_due()
    except (psycopg.errors.UndefinedFunction, psycopg.errors.UndefinedColumn):
        print("Notice emails were not sent, because migration 0031 is not applied to this "
              "database.")
        return False
    except Exception as err:  # noqa: BLE001  the sync above has already been committed
        print(f"Notice emails could not be listed: {type(err).__name__}: {err}")
        return True
    if summary["state"] == "unconfigured":
        print("Notice emails were not sent, because RESEND_API_KEY is not set on this job.")
        return False
    print(f"Notice emails: {summary['sent']} sent, {summary['not_emailed']} not emailed by rule, "
          f"{summary['retry']} refused and kept for another try, {summary['failed']} failed "
          f"for good, across {summary['accounts']} account(s), {summary['errors']} with an error.")
    return summary["failed"] > 0 or summary["errors"] > 0


if __name__ == "__main__":
    results = run_due()
    print(json.dumps(results, indent=2, default=str))
    failed = [r for r in results if "error" in r]
    print(f"{len(results)} shop(s) run, {len(failed)} with an error.")
    exports_failed = scheduled_exports()
    emails_failed = notice_emails()
    state, sentence = data_api_guard.check()
    print(sentence)
    sys.exit(1 if failed or exports_failed or emails_failed or state == "on" else 0)
