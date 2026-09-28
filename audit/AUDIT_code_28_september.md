# Code audit, content and structure, 28 September 2026

The owner asked for a complete audit of the code's content and structure. This covers the
whole repository at `main` commit `c47e6f4`. Every finding below came from running
something or from reading the line it names, and each one states which. Nothing here has
been changed yet. Each fix waits for the owner's approval, as the standing instructions
require.

## How it was checked

| Check | Tool | Result |
|---|---|---|
| Correctness lint, the repository's own rules | `ruff check .` | Clean |
| Wider lint, counted rather than enforced | ruff with security, complexity and bug rules | 1,308 findings, most of them style. The security and complexity ones are read below |
| Service tests | the five `tests/test_*.py` harnesses | All pass: 15, 9, 8 and 45 cases, and the conformance check |
| Contract coverage | the FastAPI schema against `api/openapi.yaml` | 27 of 58 operations served |
| Front end types | `openapi-typescript` regenerated and compared | `api-types.d.ts` matches the contract exactly |
| Python dependencies | `pip-audit` | No known vulnerabilities |
| Front end dependencies | `npm audit`, `npm outdated` | 5 advisories, 3 low and 2 moderate, all inside Stack's sign-in package |
| Dead code | `vulture`, then a search for each candidate | 5 unused names confirmed |
| Complexity | `radon cc` and `radon mi` | 5 functions graded D, E or F |
| Credentials | `gitleaks git` over the whole history | Nothing found |
| Idempotency under load | 8 threads sending one key at once, on the local copy of development | A fault, below |
| Return address validation | 6 crafted values sent to the authorise endpoint | A fault, below |
| Database cost of a request | `pg_stat_database` before and after one call | 4 or 5 transactions each |

The service ran against the local PostgreSQL 16 built for the QA of 25 September, whose
schema and ledger match Neon's development branch exactly (`audit/QA_end_to_end_25_september.md`).

## Summary

| Severity | Finding | Where |
|---|---|---|
| High | Neither half of the build is pinned, so a deploy installs whatever versions resolve that day | `.gitignore`, `service/requirements.txt` |
| High | Billing starts a Stripe subscription and records nothing, and the webhook discards every event | `service/app/billing.py` |
| High | A seller cannot delete their account, export their data or disconnect their shop | 3 contract operations not served |
| Medium | A repeated Idempotency-Key sent at the same moment returns 500 instead of the first answer | `service/app/idempotency.py` |
| Medium | The TikTok return address accepts tab and newline characters that a browser reads as another site | `service/app/connections.py` |
| Medium | The service makes two log calls, and nothing reports an error to anyone | `service/app` |
| Medium | Every request costs 4 or 5 database transactions, and Today fetches its own figures twice | `db.py`, `shops.py`, `AppBar.jsx` |
| Medium | The tests are hand-written scripts with no coverage measure, and the smoke tests match SQL by substring | `service/tests` |
| Medium | Three faults stop a database being built from the repository alone | `migrate.py`, `0011`, `seed.sql` |
| Low | Five unused names | `auth.py`, `connections.py`, `money.py` |
| Low | Three notes in the code state things that are no longer true | `idempotency.py`, `money_view.py`, `today_view.py` |
| Low | The same severity is called "Urgent" on one screen and "Act now" on another | two page files |
| Low | The browser sends cookies to a service that reads none | `web/src/lib/api.js`, `main.py` |
| Low | Five functions are too complex to test with confidence | `money_view.py`, `products.py`, `cost_files.py`, `today_view.py` |
| Low | Stack's sign-in package carries 5 advisories with no upgrade that clears them | `web/package.json` |
| Low | The repository root holds 36 files, and the root README is one line | root |

## High

### H1. The builds are not reproducible

**Read.** `.gitignore` excludes `web/package-lock.json`, and `ci.yml` says so: "There is no
lockfile". `package.json` pins Stack at `2.8.108` and the fonts exactly, but gives Next.js,
React and Stripe as ranges such as `^15.1.6`. `service/requirements.txt` gives every
package as a lower bound only, for example `fastapi>=0.115`.

**Why it matters.** Vercel and Render each install whatever satisfies those ranges on the
day of the deploy. A faulty release of any dependency reaches production without passing
through CI first, because CI installs its own fresh copy on a different day. The versions
running now cannot be stated from the repository.

**Proposed fix.** Commit `web/package-lock.json` and install with `npm ci` in CI. Generate a
pinned `service/requirements.lock` (for example with `pip-compile`) and install from it on
Render and in CI, keeping `requirements.txt` as the list of direct needs.

### H2. Billing is not connected to the database

**Read.** `start_trial` creates a Stripe customer and subscription and returns. It writes
no row, although migration 0018 built `subscriptions` and a `create_subscription`
function for this. `stripe_webhook` verifies the signature, then does nothing for the three
events it names and answers `{"received": true}`, so Stripe records them as delivered and
will not send them again. `CLAUDE.md` already says "nothing is wired to them yet".

**What this audit adds.** Nothing checks for an existing subscription, so each new
Idempotency-Key starts another trial for the same seller. `_find_or_create_customer`
relies on Stripe's customer search. Stripe's search page (docs.stripe.com/search) says
"Don't use search for read-after-write flows" and that data is searchable "in under 1
minute", so two calls within that minute can create two customers. Any `invoice.payment_failed` event delivered
before the handlers exist is acknowledged and lost.

**Proposed fix.** Before billing goes live: record the subscription through
`create_subscription` in the same request; refuse a second trial for an account that has
one; store each webhook event id and apply it through `apply_subscription_event`; and answer
Stripe with an error, so that it retries, until a handler exists.

### H3. Three rights a seller needs are not served

**Run.** Of the contract's 58 operations, 31 are not served. Most wait on rulings or on
TikTok, as `CLAUDE.md` records. Three matter before any real seller signs up:

- `DELETE /me` (`deleteMe`) and `POST /me/export` (`requestAccountExport`). UK data
  protection law gives a person the right to erasure and to a copy of their data, and the
  project's own `MyShopEdge_Data_Protection.docx` promises both: "Erasure (Art. 17) In-app
  'Delete my account' with export prompt" and "Portability (Art. 20) Machine-readable export
  (CSV and JSON)".
- `DELETE /shops/{shopId}/connection` (`disconnectShop`). A seller who connects a shop has
  no way to withdraw MyShopEdge's access from inside the product.

`GET /billing/subscription` is also unserved, so no screen can show a seller which plan
they are on.

## Medium

### M1. A repeated Idempotency-Key at the same moment returns 500

**Run.** Eight threads sent one stock adjustment with one key at the same instant. The
database gained exactly one movement, so the data stayed correct. Two callers received 201.
Six received `500 internal_error`, and the service log shows six `UniqueViolation` errors.

**Why.** `replay` reads the key without locking it. Every concurrent request finds no row,
does the work, and then all but one fail on the primary key of `idempotency_keys`. The
failed transactions roll back, which is why the data is right. The caller is still told the
save failed, and a phone that retries a slow save is exactly this case.

**Proposed fix.** Take a transaction-scoped advisory lock on the account, operation and key
before `replay` reads, so the second request waits and then replays the first answer. A
smoke case and the thread test above would cover it.

### M2. The return address accepts characters a browser strips

**Run.** The authorise endpoint refused `//evil.example` and `/\evil.example`, as intended,
and accepted `/<tab>/evil.example`, `/<newline>/evil.example` and `/%2F%2Fevil.example`.
Browsers remove tabs and newlines from an address, so the first two become
`//evil.example`, which is another site.

**Why it is latent.** The site's return page ignores `return_to` and always links to
`/shops`, so nothing redirects today. The contract describes this field as an account
takeover risk, and the service stores and returns whatever passed the check.

**Proposed fix.** Refuse any control character and any percent sign in `return_to`, or
compare it against a short list of the site's own paths.

### M3. The service logs almost nothing

**Read.** `service/app` makes 2 logging calls: the auth claims warning in `auth.py` and the
unhandled error in `main.py`. No request is logged with its route, status and time. No error
reporting service is connected. A seller's failed request leaves one stack trace in
Render's log and no other trace.

**Proposed fix.** One middleware line per request (method, route template, status,
milliseconds, and no identifiers), and an error reporter for 500s, such as Sentry.

### M4. Each request costs several database round trips

**Run.** One call to `/today`, `/money` or `/products` cost 5 transactions, and `/me` cost 4.
`require_account` opens one to resolve the account, `require_shop` opens a second to check
the shop, and the handler opens a third. The Today page then asks for `/today` itself, and
`AppBar.jsx` asks for `/today` again for its freshness stamp, plus `/notifications` and
`/shops`.

**Why it matters.** Render's free plan and Neon's smallest compute are what the product
runs on. One load of Today makes four API calls, `/today` twice, `/shops` and
`/notifications`, which measured 5, 5, 4 and 4 transactions: 18 in all.

**Proposed fix.** Resolve the account and check the shop inside the handler's own
transaction, and pass the Today figures to the top bar rather than fetching them twice.

### M5. The tests cannot say what they cover

**Read.** The tests are scripts that print PASS and FAIL rather than a test framework, so
no coverage figure exists. `test_handlers_smoke.py` answers each query by finding a piece
of its SQL text. The file says so honestly, and it is the reason the QA of 25 September
found faults the smoke tests had passed: a query that changes can still match a canned
answer written for the old one.

**Proposed fix.** Run the harnesses under pytest with coverage, and move the checks that
matter most, the money arithmetic and the tenancy refusals, onto the local database that
`audit/qa_25_september/rebuild.sh` builds.

### M6. A database cannot be built from the repository alone

These three were found on 25 September and are unchanged. `migrate.py` fails from empty
because the base file already contains 0001 to 0009. Migration 0011 reads a table that only
0016 creates. `testdata/seed.sql` leaves out two required columns. Until they are fixed,
nobody can stand up a working copy without the steps in `rebuild.sh`.

## Low

### L1. Unused code

Confirmed by searching for each name across the repository: `_origin_of` and `_base_url`
in `auth.py`, `REFRESH_URL` in `connections.py` (the refresh is not built), and `allocate`
and `from_decimal_string` in `money.py`. `testdata/ingest.py` keeps its own `allocate`.
`api/patch_contract_2026-09-22.py` and `design/figma_pending_changeset.js` are one-off
scripts that nothing references, and the first writes to a scratch path from an old session.

### L2. Notes that are no longer true

- `idempotency.py` says migration 0023 is "not yet applied". It is applied on all three branches.
- `money_view.py` and `today_view.py` say the handler has not run against a real database.
  Both ran against the local copy of development on 25 September and matched the ledger.

### L3. One severity, two words

`today/page.jsx` calls a critical item "Act now". `notifications/page.jsx` calls it
"Urgent". Each file defines its own `SEVERITY_WORD`, while A8's words live in `lib/terms.js`
for exactly this reason.

### L4. Cookies are sent for nothing

`api.js` sets `credentials: "include"` and `main.py` sets `allow_credentials=True`. The
service reads only the bearer token. Removing both narrows what a browser sends across
origins, and changes nothing a seller sees.

### L5. Complexity

`radon` grades `money_view.calculate` F (47 paths), `products.list_products` E (35),
`products.get_product` D (30), `cost_files.match` D (24) and `today_view._needs_you` D (23).
These are the functions that hold the financial rules, so they are where a fault is both
most likely and most costly. Each would split along the sections it already comments.

### L6. Stack's advisories

`npm audit` reports `elliptic` (low) and `uuid` (moderate) inside `@stackframe/stack-shared`,
reaching the site through `@stackframe/stack` 2.8.108. npm's only offered remedy is Stack
2.5.30, which is older. They cannot be cleared from this repository. CI fails only on high
and critical advisories, so it passes.

### L7. Structure

- The root holds 36 files: 28 rulings (`A2` to `A29`), five other documents, `ruff.toml` and
  `skills-lock.json`. The rulings would sit better in `rulings/`, with links updated.
- `README.md` is the single line `# My-ShopEdge`. `README_v0.2.md` is the real one and is
  what GitHub does not show first.
- `project-source/` holds nine Word documents and an older `MyShopEdge_MVP_schema.sql` that
  differs from `schema/`. A second schema file is a trap for whoever finds it first.
- `testdata/` uses SHA-1 to make stable test ids. That is not a security use and needs no
  change.

## What was checked and found sound

- **SQL.** ruff flagged 12 queries as possible injection. Each was read. Every value a
  caller sends is a bound parameter, and the text built into the SQL comes only from fixed
  lists in the code.
- **Tenancy and authentication.** The QA of 25 September refused every bad, expired and
  forged token and kept a second seller out of every route. Those results stand.
- **Secrets.** gitleaks finds nothing in the history. Both `.env.example` files hold names
  and placeholders only, and the one real-looking value is Stack's public project id.
- **Python dependencies.** pip-audit finds no known vulnerability.
- **The contract.** Every served route is in the contract, and the front end's generated
  types match it exactly.
- **Error handling.** An unhandled error becomes a problem response inside the CORS layer,
  so a browser sees the error rather than a network failure.

## Not covered

- Stack's own sign-in pages and cookies, which run on Stack's servers.
- Anything that talks to TikTok, because no shop is connected.
- Stripe end to end, because only the live account is reachable.
- Load beyond eight concurrent requests.
