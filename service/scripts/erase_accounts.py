"""Erases every account whose thirty days under A30.1 have ended.

    DATABASE_URL=... S3_BUCKET=... python3 scripts/erase_accounts.py

It connects as the service does, runs as `mse_app`, and finds the accounts through
`accounts_due_for_erasure()` from migration 0025. It is safe to run as often as wanted: an
account is erased once, and one that fails part way stays due for the next run.

**Nothing schedules it yet.** It has run against the local copy of development and a local
stand-in for S3, on 28 September 2026, and never against Neon or a real bucket. A Render cron
job running it daily is the owner's to create.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.account_deletion import erase_due  # noqa: E402

if __name__ == "__main__":
    done = erase_due()
    print(json.dumps(done, indent=2))
    print(f"{len(done)} account(s) erased.")
