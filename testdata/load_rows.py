"""Load a rows file written by ingest.py into a database built by service/scripts/migrate.py.

    DATABASE_URL=postgresql://... python3 testdata/load_rows.py testdata/rows_year.json

Written 29 September 2026. Nothing in the repository turned `rows.json` into a database:
`seed.sql` was edited by hand and the QA of 25 September found it does not load (fault 6).
This inserts every table in the order ingest.py writes them, in one transaction.

One value is supplied that the rows do not carry. `tiktok_connections.access_token_enc` and
`refresh_token_enc` are `not null`, and a synthetic shop has no tokens, so each gets the same
one-byte placeholder the development branch holds. Nothing can decrypt it, which is right.

It must connect as a role that owns the tables or bypasses row level security, because it
writes every tenant's rows. It is for local copies and never for a Neon branch.

**Run on 29 September 2026** against a database built from empty by `migrate.py`, loading
`rows_year.json` (233 ledger entries) with no error.
"""

import json
import os
import sys

import psycopg
from psycopg.types.json import Jsonb

PLACEHOLDER = b"\x00"


def load(url: str, path: str) -> dict:
    rows = json.load(open(path))
    counts = {}
    with psycopg.connect(url) as conn, conn.transaction():
        for table, items in rows.items():
            for item in items:
                item = dict(item)
                if table == "tiktok_connections":
                    item.setdefault("access_token_enc", PLACEHOLDER)
                    item.setdefault("refresh_token_enc", PLACEHOLDER)
                cols = list(item)
                vals = [Jsonb(v) if isinstance(v, dict) else v for v in item.values()]
                conn.execute(
                    f"insert into {table} ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))})",
                    vals,
                )
            counts[table] = len(items)
    return counts


if __name__ == "__main__":
    url = os.environ.get("DATABASE_URL")
    if not url or len(sys.argv) != 2:
        raise SystemExit("usage: DATABASE_URL=... python3 load_rows.py <rows.json>")
    print(load(url, sys.argv[1]))
