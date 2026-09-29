"""The migration runner.

    DATABASE_URL=postgresql://... python3 scripts/migrate.py --status
    DATABASE_URL=postgresql://... python3 scripts/migrate.py

Why this exists. On 22 September 2026 the development and production branches were found
to have diverged in both directions, because fourteen migrations had been applied by hand
with no record in either database. Nothing could state which branch held what, so nobody
noticed. Every branch now records its own position and this runner is the only thing that
writes to that record.

Three rules it enforces.

1. A migration is applied once. A filename already present is skipped, not re-run.
2. An applied migration is never edited. If a recorded checksum no longer matches the file
   on disk, the runner refuses to do anything at all, because once a migration has changed
   under a branch the branches can never be compared again.
3. Each migration runs in its own transaction, and its ledger row is written inside that
   same transaction. A migration that fails leaves no row, so a retry is safe.

The runner connects as mse_migrator. It does not connect as mse_app, which has no rights
over the ledger and no business changing the schema.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

import psycopg

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"

# The base schema first, then every numbered migration in order. Files that are not
# migrations, such as the verification scripts, are excluded by name rather than by
# guesswork, so adding one cannot accidentally make it run.
BASE = "MyShopEdge_MVP_schema_v0.2.sql"
NOT_MIGRATIONS = {"verify_v0.2.sql", "verify_v0.2_as_app.sql"}

LEDGER = """
create table if not exists schema_migrations (
  filename   text primary key,
  checksum   text        not null,
  applied_at timestamptz not null default now(),
  applied_by text        not null default current_user,
  backfilled boolean     not null default false
)
"""


# Building from empty, fixed 29 September 2026 after the QA of 25 September found that it
# could not be done (audit/QA_end_to_end_25_september.md, faults 4 and 5).
#
# The base file already holds migrations 0001 to 0009, each marked by a line such as
# `-- ---------- 0001_roles_and_grants.sql`, and 0002 fails when run a second time. When the
# base file is applied, the migrations it names are recorded as backfilled rather than run,
# which is how the Neon branches were recorded. The names are read from the file itself.
INCLUDED = re.compile(r"^-- ---------- (\d{4}_[a-z0-9_]+\.sql)\s*$", re.MULTILINE)

# 0011 reads neon_auth.users_sync, which only 0016 creates on a branch Neon Auth does not
# reach. 0016 does nothing where the table exists, so running it first is safe.
RUN_FIRST = {"0011_identity_bridge.sql": "0016_neon_auth_standin.sql"}


def included_in_base(base: Path) -> list[str]:
    return INCLUDED.findall(base.read_text())


def migration_files() -> list[Path]:
    numbered = sorted(
        p for p in SCHEMA_DIR.glob("*.sql")
        if p.name[0].isdigit() and p.name not in NOT_MIGRATIONS
    )
    base = SCHEMA_DIR / BASE
    return ([base] if base.exists() else []) + numbered


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    status_only = "--status" in sys.argv
    files = migration_files()

    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(LEDGER)
        applied = {
            row[0]: row[1]
            for row in conn.execute("select filename, checksum from schema_migrations")
        }

    # Rule 2, checked before anything is applied.
    changed = [
        p.name for p in files
        if p.name in applied and applied[p.name] != checksum(p)
    ]
    if changed:
        print("Refusing to run. These applied migrations have changed on disk:", file=sys.stderr)
        for name in changed:
            print(f"  {name}", file=sys.stderr)
        print(
            "\nAn applied migration must never be edited. Write a new one that corrects it.",
            file=sys.stderr,
        )
        return 2

    pending = [p for p in files if p.name not in applied]

    if status_only:
        print(f"{len(applied)} applied, {len(pending)} pending")
        for p in pending:
            print(f"  pending  {p.name}")
        return 0

    if not pending:
        print(f"Up to date. {len(applied)} migrations applied.")
        return 0

    by_name = {p.name: p for p in files}
    done: set[str] = set()
    count = 0
    for path in pending:
        if path.name in done:
            continue
        first = RUN_FIRST.get(path.name)
        if first and first in by_name and first not in applied and first not in done:
            with psycopg.connect(url) as conn:
                table = conn.execute("select to_regclass('neon_auth.users_sync')").fetchone()[0]
            if table is None:
                count += _apply(url, by_name[first], note=f" (before {path.name}, which needs it)")
                done.add(first)
        count += _apply(url, path)
        done.add(path.name)
        if path.name == BASE:
            for name in included_in_base(path):
                if name in by_name and name not in applied:
                    _record_backfilled(url, by_name[name])
                    done.add(name)

    print(f"\n{count} applied.")
    return 0


def _apply(url: str, path: Path, note: str = "") -> int:
    print(f"applying {path.name}{note} ... ", end="", flush=True)
    # Rule 3: the migration and its ledger row share one transaction.
    with psycopg.connect(url) as conn:
        with conn.transaction():
            conn.execute(path.read_text())
            conn.execute(
                "insert into schema_migrations (filename, checksum) values (%s, %s)",
                (path.name, checksum(path)),
            )
    print("done")
    return 1


def _record_backfilled(url: str, path: Path) -> None:
    print(f"recording {path.name} as backfilled, because {BASE} contains it")
    with psycopg.connect(url) as conn:
        conn.execute(
            "insert into schema_migrations (filename, checksum, backfilled) values (%s, %s, true)",
            (path.name, checksum(path)),
        )


if __name__ == "__main__":
    raise SystemExit(main())
