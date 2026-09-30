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

The secrets come from the environment and are never printed. The output names shops by
MyShopEdge id and gives TikTok's own error code and message when a call is refused.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tiktok_sync import run_due  # noqa: E402

if __name__ == "__main__":
    results = run_due()
    print(json.dumps(results, indent=2, default=str))
    failed = [r for r in results if "error" in r]
    print(f"{len(results)} shop(s) run, {len(failed)} with an error.")
    sys.exit(1 if failed else 0)
