# MyShopEdge. Instructions for Claude Code

Written 23 September 2026, when the project moved from a hosted session to Claude Code
running on Adenola's own machine. Everything a new session needs is here, so no previous
transcript has to be read.

## What this is

MyShopEdge is a bookkeeping and finance application for UK TikTok Shop sellers. It reads a
seller's orders, returns and settlement statements from TikTok, holds them in a double entry
ledger, and shows the seller what they actually earned rather than what TikTok paid out.

The owner is Adenola Adegbesan, trading through Inspirecraft Global Ltd, Leicester, which is its registered name.

## How to work on it

These are standing instructions from the owner. They hold until he changes them.

1. **One action at a time, and get approval before proceeding.** He lifted this for a
   defined batch once. Treat it as in force unless he lifts it again for a named batch.
2. **No secret is ever typed into the conversation.** Not the TikTok app secret, not a
   database password, not a Stripe key. Secrets travel through environment variables or
   through his own terminal.
3. **Never create products or prices in the live Stripe account `acct_1RtsbgKUYBix7r5t`**
   without an explicit instruction. Stripe prices are immutable once created.
4. **Write in his house style.** Every sentence carries a subject and a verb. No em dashes
   and no en dashes. No clipped marketing phrases. Modest things are described honestly
   rather than inflated. Nobody is praised by diminishing anybody else.
5. **Do not end a reply with a next steps recommendation.** Answer what was asked and stop.
   He sets the agenda.
6. **Run the query rather than reading the code.** Every serious fault on this project was
   found by executing something, and none were found by reading. The list is in the section
   on faults below.
7. **No assumption coding. Facts only.** This is a hard rule and it outranks speed.

   A fact is something that was read from the file, returned by the query, printed by the
   call, or written in the vendor's own documentation. Everything else is an assumption,
   including a recollection of what a file contains, a reasonable inference about how an
   API behaves, and a memory of a decision taken earlier in the project.

   In practice this means five things.

   - Before stating what code does, open it. Do not describe a function from its name.
   - Before stating what an API returns, call it or cite the vendor's page. A field is not
     present because it would be sensible for it to be present.
   - Before stating what a table holds, query it. A migration having been written is not
     evidence that it was applied.
   - When a fact cannot be obtained, say so plainly and name what is unknown. An unanswered
     question recorded as unanswered is worth more than a plausible guess, because the guess
     gets built on.
   - Mark unverified work as unverified, in the file itself rather than in a message. A
     script that has never run says so at the top.
   - **A vendor's documentation is not a fact about this project.** It describes what the
     vendor generally does. What this installation runs is in its own configuration, and
     reading that costs one call. On 23 September a documentation page was taken as
     evidence about this project twice, and both times the configuration said something
     different. The second time it would have stopped every seller signing in. See A25.

   The reason is on the record. Authentication verified the wrong signing algorithm for a
   day, and its tests passed because the fixtures were generated from the same assumption.
   Five views leaked across tenants while a row level security check that queried base
   tables reported clean. The settlement endpoint was pinned to an API version that omits
   every reserve field, on the strength of a document rather than a call. None of these were
   careless. Each was a reasonable assumption that nobody checked.

## The contract is the source of truth

`api/openapi.yaml` holds 61 operations across 56 paths. Rule 1 of A13 says the service
implements the contract and never the other way round. A test enforces it:

```
cd service && python3 tests/test_contract_conformance.py
```

It generates the schema from the actual FastAPI handlers and fails if anything is served
that the contract does not document. It does not check the reverse, because most paths are
not built yet and that is expected.

## Where the build actually stands

The specification is close to complete. The application is not. As of 23 September:

| Layer | State |
|---|---|
| Rulings, terminology, screens, data model, API contract | Done |
| Schema | Through 0025 on all three branches, with 26 migrations recorded on each. **0026, the export jobs, and 0027, the list of shops the TikTok sync reads, were applied on 29 September with the owner's authority to development and then production**, each in one transaction with its record and the file's SHA-256. Queried afterwards on production: 28 migrations recorded, `shops_due_for_sync()` belongs to `mse_migrator` and only `mse_app` may call it, `account_exports` forces row level security, and neither `authenticated` nor `anonymous` holds any right on either. Neither is on staging. 0025, account deletion, was applied on 29 September with the owner's authority, development first, then staging, then production, each in one transaction with its `schema_migrations` row and the file's SHA-256. Queried afterwards on all three: the record and checksum match, `accounts.erased_at` exists, both new functions belong to `mse_migrator` and only `mse_app` may call them, and on production neither `authenticated` nor `anonymous` can. The note inside 0025 saying it is not applied to any Neon branch is stale and stays, because an applied migration is never edited. The three schema fingerprints matched exactly when last compared on 24 September, before 0025. 0022, 0023 and 0024 were applied on 24 September with the owner's authority through the Neon connection, which runs as `mse_migrator`, rather than through `migrate.py`, so that no connection string entered the session. Each migration and its `schema_migrations` row went in one transaction with the file's SHA-256, as the runner does, so `migrate.py --status` reads them as applied. The notes inside 0022 and 0023 saying "not yet applied" are stale and stay, because an applied migration is never edited. See the Data API section below for 0024 |
| Backend | 55 of 56 contract paths and 60 of 61 operations, counted from the generated schema on 29 September. The one operation not served is `getExpectedPayouts`, for the reason in the blocked table. Added on 29 September: `getTrends`, `getInsights` (A31.1), the four export operations and `listSkuCosts`. `getAccountExport` and `listSkuCosts` were added to the contract with them, because a job could not be polled and S20 had no list to read |
| Authentication | **Verified by a real sign-in on 24 September.** ES256 verified against the provider's fetched JWKS, email read from `users_sync`, 15 tests passing. The first real token logged `iss` `https://api.stack-auth.com/api/v1/projects/f1762e29-4750-42f6-80e1-c94b040a72e8` and `aud` `f1762e29-4750-42f6-80e1-c94b040a72e8`, and both are set on Render as `NEON_AUTH_ISSUER` and `NEON_AUTH_AUDIENCE`. The next request created the first production account at 15:17:21 UTC |
| Billing | Screens built. The three products and prices exist in the live Stripe account as of 23 September. Nothing is wired to them yet |
| TikTok integration | **Connected to two real shops and syncing, 29 September 2026.** The account `inspirecraftglobal@gmail.com` holds IkonetU (`GBGBLCUKQTCE`, TikTok shop id `7494930319769175829`), connected at 17:52 UTC, and My ShopEdge (`GBGBLCRKQTEX`, `7494921934920582817`), connected at 21:32 UTC, each through its own approval of the same Seller Developer custom app (A31.6, A31.7). `_sign`, the shop cipher and the stored tokens work against the live API. The Render cron job `My-ShopEdge-sync` (`crn-dau1er8u01pc73asut8g`, plan `0.5c-512mb`, Frankfurt, daily at 05:47 UTC) runs `scripts/sync_shops.py`. Its run at 21:34 UTC read both shops without an error. My ShopEdge gave 1 order, `576955651451099542`, one item at £8.00 placed 23 September and CANCELLED, and 1 statement, `7689354716446639894`, dated 26 September with a payout of £0.00, which posted gross sales 800, refund -800 and settlement 0 in September. IkonetU gave nothing in two years. No real statement has yet carried a fee, commission, postage or reserve, so those parts of the ledger posting are still checked only against generated payloads. No token refresh has reached TikTok yet. Order money is posted once, at settlement (A31.5). See A23, A27, A28 and A31 |
| Front end | All 36 screens built. The ten added on 29 September are S3, S4, S5, S20, S23, S31, S35, S36, S37 and S38, each driven in a browser against the local copy of development. The rest are S1, S2, S6 to S17, S21, S22, S24 to S30, S32, S33 and S34, plus the closing page A30.1 needs, because neither page exists. `SCREENS.md` is the register |
| Figma | Unreadable. The Starter plan call limit refuses every read of the file, on 22 and 24 September. It holds frames that predate A15, so it is out of date whatever it holds. `SCREENS.md` explains. The wireframes are committed at `design/wireframes/` |
| Deployment | The front end is live on Vercel production and redeploys on every merge to `main`. The service runs on Render as `My-ShopEdge-1` at `https://my-shopedge-1.onrender.com`, Frankfurt, free plan, and redeploys on every merge to `main`. The owner chose Render for the MVP on 24 September, with a move to a UK host later. Vercel reaches it through `NEXT_PUBLIC_API_BASE_URL` |

The honest summary is that the thinking is done and the building has started.

## The documents

`A2` to `A30` are the rulings, one file per action. A29 holds the dashboard rules and the
rule that Python owns every financial and business rule. **A29.11 sets which document wins:
the product rulings and the contract govern the master engineering skill, and a provider's
documentation governs only facts about that provider.** A29.12 states why MyShopEdge exists. They are decisions rather than notes, so
a ruling is changed by editing its document rather than by remembering a conversation.

`README_v0.2.md` carries the running status, the open items by owner, and the account wiring.
Update it when a decision changes, because it is the file he reads first.

`RUNBOOK_tiktok_connection.md` is the five step procedure for connecting a real shop. It is
written to be followed once.

## The infrastructure

| Piece | Value |
|---|---|
| Database | Neon project `super-mouse-64697125`, PostgreSQL 16, `aws-eu-west-2`, London |
| Branches | production `br-plain-sea-zaphlsmw`, staging `br-little-rice-zatxxnda`, development `br-little-mode-zagjq5bg` |
| Neon account | The direct account under adenola.adegbesan@gmail.com |
| Identity | Neon Auth provisioning **Stack Auth**. `auth_provider: stack` in the project's own configuration. JWKS on `api.stack-auth.com`, signing **ES256** |
| GitHub | `Adenola777/My-ShopEdge` is the one Vercel is wired to. `MyShopEdge-` also exists |
| Vercel | team `coterie448-8267's projects`, project `my-shop-edge`, root `web`, functions in `lhr1` |
| Stripe | live `acct_1RtsbgKUYBix7r5t`, sandbox `acct_1Rtsby4GHrXoTk1L` |
| Product website | `site/index.html`, Vercel project `myshopedge-site` (`prj_4eDTaOTCZOZ1WOaoVu97uNbLQIWr`), root `site`, for `myshopedge.inspirecraftglobal.com`. The domain is on Namecheap, so its DNS records are the owner's to add. Its `vercel.app` addresses sit behind Vercel sign-in; the custom domain is public |

**The account split matters.** GitHub and Vercel sit under coterie448@gmail.com. Neon sits
under adenola.adegbesan@gmail.com. A third Neon project, `holy-glitter-85206770`, was
provisioned through the Vercel Marketplace and therefore lives in a Neon organisation that
Vercel creates and manages, which is why a direct account API key cannot see it. It holds
none of the work. The product runs on `super-mouse-64697125`.

The Next.js front end never touches the database. It calls the API over HTTP through
`NEXT_PUBLIC_API_BASE_URL`. Any `DATABASE_URL` sitting on the Vercel project is inert.

## Emergent AI's copy of this repository

`Adenola777/MYSHOPEDGE` is a public copy of this repository made on 25 September, on which
Emergent AI (`emergent-agent-e1 <github@emergent.sh>`) made 14 commits on 25 and 27
September. None of them is in this repository, and nothing deploys from that copy.
`audit/EMERGENT_review_28_september.md` lists every change with a verdict: worth taking,
worth taking once fixed, or not taken and why. The owner approved bringing the useful work
across on 28 September. The copy step was refused by that session's safety check, so it has
not happened. Treat Emergent's claims of passing tests as claims: its code fails this
repository's contract test and lint.

## The demo shop, set up 29 September 2026

TikTok's review blocks a real connection (A24), so the owner chose on 29 September to walk
the dashboard on made-up data. Nothing in it touches production data.

| Piece | Value |
|---|---|
| Service | Render `My-ShopEdge-demo`, `srv-datltbflot8c7383bnf0`, `https://my-shopedge-demo.onrender.com`, free plan, Frankfurt, deploys branch `claude/gifted-ride-rmmuc6` |
| Database | The development branch. `DATABASE_URL` is set by the owner in Render, never in this session |
| Data | `testdata/load_demo.py` gives `inspirecraftglobal@gmail.com` a shop named "Demo shop (sample data)" from the year dataset, with costs from 1 January 2025 and a Growth trial whose customer id begins `demo_`. It runs before the service starts and adds nothing once the shop exists |
| Site | The Vercel preview of `claude/gifted-ride-rmmuc6`, whose `NEXT_PUBLIC_API_BASE_URL` is set for that branch alone to the demo service. Its address is on the sign-in allow-list of the production branch |
| Schema | 0026 and 0027 were applied to the development branch on 29 September, each in one transaction with its record and checksum, and to production the same day |

## The database rules that are easy to break

Four hand rolled roles exist: `mse_owner`, `mse_app`, `mse_analytics`, `mse_migrator`.
`FORCE ROW LEVEL SECURITY` is on, and `app_account_id()` scopes every tenant query.

**Every view must carry `security_invoker = true`.** Without it a view runs as its owner.
`mse_migrator` holds `BYPASSRLS`, so a view without that setting bypasses row level security
entirely. Migration 0019 fixed five views that leaked across tenants and added a `DO` block
that raises if any public view lacks the setting. Adding a view without it will fail that
check, and that is deliberate.

## The Neon Data API is off, and must stay off

On 24 September the Neon Data API was found active on production, exposing `public` over
HTTP to any signed in Stack user as the role `authenticated`. A default privilege on
`mse_migrator` granted that role every right on every new table, sequence and function.
Tenant tables held, because a Data API client cannot set `app.account_id`, but
`schema_migrations` and `reference_rules` were writable and the six SECURITY DEFINER
functions were callable, including `create_subscription` and `apply_subscription_event`.
Production held no accounts, so nothing was harmed.

The Data API on production was deleted the same day, and migration 0024 revoked every right
`authenticated` and `anonymous` held in `public`, removed the default privileges, and dropped
Neon's sample table `playing_with_neon`. Its closing check raises if either role regains a
table right or a SECURITY DEFINER function. The product never uses the Data API: the front
end calls the service and the service connects as `mse_app`. Do not switch it back on.

## Faults that cost real time, so they are not repeated

Each of these was found by running something, and each survived reading.

1. **Five views leaked across accounts.** Proven by scoping to an account owning nothing.
   The base tables returned 0 and 0. `settlement_reconciliation` returned 3,
   `settlement_totals_check` returned 3 and `return_reconciliation` returned 7. The leak
   was invisible with one account, and the earlier check had queried base tables.
2. **Authentication verified the wrong algorithm.** The code checked ES256 and RS256 against
   a provider that signs ES256. It was then "corrected" to EdDSA, which was also wrong, and
   the tests were rewritten to share the new assumption and passed again. Every real token
   would have been refused either way. The
   old tests passed because the fixtures were signed with the same wrong assumption. There
   test now asserts `ALGORITHMS` against a recorded copy of the provider's real JWKS, so
   changing it without refetching fails in either direction.
3. **Settlement detail was pinned to the wrong API version.** A11 said finance `202309`,
   which returns 69 fields. The reserve fields exist only in `202501`, which returns 131.
   Using 202309 would have dropped every reserve. A17 corrects it.
4. **A GROUP BY fault in the settled orders query.** It ordered by `o.order_created_at`,
   which is not in the GROUP BY. Fixed to `order by min(o.order_created_at)`.
5. **The development ledger has no cash basis.** Found 24 September by querying it.
   `settlement_month` is empty on all 119 ledger entries, including the 88 that carry a
   `settlement_id`, because `testdata/seed.sql` left the column out. The seed is now rebuilt
   from `rows.json` (A29.10), but the development branch has not been reloaded. The ledger
   is append-only, so reloading it needs the owner's approval.
6. **A4.119 was wrong about return postage.** It said return postage never passes through
   a TikTok statement. The real payload carries `return_shipping_fee_amount` on every
   transaction, and the test payout of 453.88 is settled net proceeds of 458.38 less 4.50 of
   postage. The owner ruled that postage is reconciled, not dropped (A29.7), and Shop Money
   on Today now reads a Paid out of 453.88 with the postage stated on its own line.
7. **The test data parsed money through `float`.** Found 24 September by the new lint and a
   search. `testdata/ingest.py`, `ingest_order_export.py` and `generate_payloads.py` computed
   pence as `round(float(s) * 100)`, which A13 rule 3 forbids. On three-decimal inputs such as
   "1.005" it gives 100 where `Decimal` gives 101. All 81 distinct amounts in the payloads give
   the same pence either way, so `rows.json` and every payload regenerated byte for byte after
   the change to `Decimal`.
8. **The test data covered two months, not twelve.** Closed on 29 September by the year
   dataset (`audit/YEAR_dataset_29_september.md`). Running it found fault 10.
9. **The first end to end QA, 24 and 25 September.** The real service ran against a local
   copy of development whose schema fingerprint, ledger and ownership matched Neon exactly,
   and the production build of the front end ran against it. 281 of 283 checks passed.
   The owner ruled on both failures and on the notification gap the same day, and after
   those changes all 305 pass. The four tooling faults remain, among them that
   `migrate.py` cannot build a database from empty and that `testdata/seed.sql` does not
   load. `audit/QA_end_to_end_25_september.md` has the detail. On 29 September `migrate.py`
   was fixed to build from empty, and `testdata/load_rows.py` loads `rows.json` in place of
   the seed.
10. **Kept over a long period used a cost that did not exist when the units sold.** Found
   29 September by the year dataset. The cost for a period was the one in force at its end,
   so twelve monthly kept bars could not sum to the year, and the tax-year set-aside carried
   today's cost. The owner ruled the same day that each unit is costed on its sale date, and
   a return at its original sale's date (A31.4). Built and rerun: the year check passes all
   24 of its checks.
11. **TikTok's token expiry was read as a duration.** Found 29 September by the first real
   authorisation of the shop `7494930319769175829` (IkonetU, GB, LOCAL). TikTok answered
   `access_token_expire_in` 1791309162 and `refresh_token_expire_in` 4912765591, which are
   Unix times: 6 October 2026 17:52:42 UTC, seven days on, and 5 September 2125. The code
   added them to now, so production stored the access token's expiry as 2083 and no
   refresh would ever have fallen due. The test data had been written as durations, the
   same assumption, so every test passed. `connections.expiry` now reads both as Unix times,
   the tests carry the real values, and `tiktok_sync_check.py` passes 36 of 36 on both
   datasets. That the refresh answer also carries Unix times is unverified until the first
   refresh reaches TikTok.
12. **The returns search refused a page of 100.** Found 29 September by the first live sync.
   A11.4 said `page_size` 1 to 100 for every listing. Orders and statements accepted 100, and
   the returns search answered code 98001004, "allowed range (10 to 50)". It now asks for 50.
   The same run's summary said "0 with an error", because it counts exceptions and not a
   step recorded as failed; `sync_runs` held the failure with TikTok's message.

## Commercial rulings worth knowing before touching billing

- The three prices are **exclusive of VAT**. Starter £9.99, Growth £24.99, Pro £49.99, each
  plus VAT. Stripe needs `tax_behavior: "exclusive"` and it has to be right first time.
- **History is twenty four months on every plan**, not tiered.
- **The order limit is enforced softly.** The count appears at eighty per cent and at a
  hundred per cent, the larger plan is offered, and nothing stops. No month closes, no
  export is withheld, no figure stops updating.
- **Cost files are Excel and CSV only.** Word and PDF carry no columns, so reading a cost
  from one means guessing, and a wrong cost is worse than a missing one.
- Bank reconciliation is out of scope, so `settlements.settlement_reference` has no
  automatic source.

## The Stripe products, created 23 September 2026

These live in `acct_1RtsbgKUYBix7r5t`, which is the live account. `plans.py` reads the price
identifier from an environment variable and never from a browser, so these three values are
what those variables hold. A price identifier is not a secret, because Stripe Checkout sends
it from the client by design.

| Plan | Product | Price | Environment variable |
|---|---|---|---|
| Starter | `prod_VJS0gANslYxL4f` | `price_1UIp77KUYBix7r5t8CZvvdaj` | `STRIPE_PRICE_STARTER` |
| Growth | `prod_VJS0v6ZFvMl3if` | `price_1UIp7CKUYBix7r5tVgIsyIfC` | `STRIPE_PRICE_GROWTH` |
| Pro | `prod_VJS1MeCHyH5b6b` | `price_1UIp7EKUYBix7r5t8LIvxFd6` | `STRIPE_PRICE_PRO` |

Each price is GBP, recurring monthly at `interval_count` 1, `usage_type` licensed, and
`tax_behavior` exclusive. The amounts are 999, 2499 and 4999 in minor units, which matches
`price_minor` in `plans.py`. The tax code on all three is `txcd_10103101`.

**One older object is in the account and must not be used.** `prod_VIt8w0nPWOoQEv`, named
plainly MyShopEdge, carries `price_1UIHMSKUYBix7r5tDtHTJgvl`. That price is one time rather
than recurring and it has no amount, because it was created as a customer chooses the amount
price. It charges nothing and it cannot be edited into shape. Archive it rather than reuse
it.

## Running things

The service needs Python 3.10 or later and the packages in `service/requirements.txt`.

```
cd service
pip install -r requirements.txt
python3 tests/test_auth_verification.py
python3 tests/test_contract_conformance.py
uvicorn app.main:app --reload
```

Neither test needs a database, credentials or the network.

The front end:

```
cd web
npm install
npm run dev
```

The database connection string belongs in the environment as `DATABASE_URL` and never in a
file inside this repository. `.gitignore` already excludes `.env` and its variants.

## What is blocked, and on what

| Item | Blocked on |
|---|---|
| Testing billing end to end | The sandbox account reaching a session. Only the live account is reachable, so no test charge can be made |
| Every claim the TikTok ingestion makes | A real shop authorisation. The runbook covers it |
| Whether twenty four months of statements exist | The same shop authorisation |
| The literal column labels on a settlement export | The same shop authorisation |
| The remaining 20 Figma screens | The Figma Starter plan call limit |
| Where the Python service runs long term | A28.4 decided a long-lived container in London. For the MVP the owner chose Render in Frankfurt on 24 September, with the move to a UK host later |
| Rotating the encryption key for `tiktok_connections.access_token_enc`, `refresh_token_enc` and `shop_cipher_enc` | The key itself is `TIKTOK_TOKEN_KEY` on Render, made by the owner in his own terminal (the runbook, step 3). Rotation is not built: nothing can hold two keys at once, so `key_version` is always written as 1, and changing the key makes every stored token unreadable |
| Whether `authorization_expires_at` is the refresh token's expiry | One real TikTok authorisation. The contract serves the field and `tiktok_connections.refresh_expires_at` looks like the same instant. Nobody has checked, so 0020 adds no column for it |
| The first real token refresh | Time. Both access tokens lapse on 6 October 2026, IkonetU at 17:52 UTC and My ShopEdge at 21:32 UTC, and the daily sync refreshes a token when fewer than two days remain, so the run of 5 October is the first that should refresh. That the refresh answer carries Unix times, like the code exchange, is unverified until then |
| Cost uploads working for a seller | The bucket's settings on Render. On 30 September the owner ruled that AWS is not used for now and created a Cloudflare R2 bucket in the EU jurisdiction (A10.8 as amended). The six cost upload operations are served since 28 September and have run only against a local stand-in, configured as R2 on 30 September (`testdata/storage_check.py`, 11 of 11). Until the owner sets the five variables in `RUNBOOK_file_storage.md` step 4 on Render, each answers 503 `storage_unconfigured`. The bucket is not visible to this session's Cloudflare connection, which listed no buckets |
| `createExport`, `getExport`, `requestAccountExport` and `getAccountExport` | The R2 bucket's settings on Render. Migration 0026 is on production since 29 September. All four are served since 29 September. Each file is built after the 202 in the service's own process, and a job still queued five minutes on is built when it is next read. They have run against the local copy and a local stand-in for S3, where every file's totals equalled the screens |
| `checkReturnItem` | Nothing now. The four rulings were made on 28 September (A30.2) |
| Erasing closed accounts on day thirty | A scheduler. `service/scripts/erase_accounts.py` does the erasure A30.1 rules and has run against the local copy and a local stand-in for S3. Nothing runs it daily until the owner creates a Render cron job. Migration 0025, which it needs, is on all three branches since 29 September |
| Any tax figure on S12 | Reference rules. Production's `reference_rules` held 0 rows when queried on 28 September, so the VAT monitor, the set-aside and the tax dates all show that nothing is loaded. The set-aside method of A30.3 is built and tested on made-up values, and uses a rule only once its `reviewed_at` is set. The figures have to be read from gov.uk, which this session's network policy refuses, and loaded with their `source_url` |
| What a deletion does to a paid plan | A ruling. A30.1 does not cover billing, so a seller who deletes the account keeps being charged by Stripe until it is ruled and built |
| `getExpectedPayouts` | A source for TikTok's unsettled orders. The contract says it is read from that endpoint, nothing ingests it, and the ledger holds the week a sale happened, not the week TikTok will pay |

## What is next in the code

On 24 September the seller's own routes, costs, the two actions and Needs you were built.
The next pieces of code are unblocked only as the blocked table above clears, except for the
contract's remaining reading operations (returns, tax, notifications, alert settings and
account deletion). `settlements.py` and `records.py` remain the pattern: keyset
pagination, RFC 9457 problem details, and the same 404 for another tenant's row as for one
that does not exist. A write follows `stock.create_stock_adjustment`: the Idempotency-Key
through `idempotency.py`, the write and its key in one transaction, and a smoke case that
replays the key. Every write is checked on the development branch as `mse_app` inside a
transaction that ends in a rollback.

<!-- BEGIN AWS Agent Toolkit rules -->
# AWS Guidance for the new AWS experience

This user has signed up for the new AWS experience. This experience lets you sign into AWS using a social provider and requires the following additional context.

Where this guidance conflicts with the project's own instructions, the project's instructions take precedence.

## Context

### Terminology:

- Say "project" instead of "account" — a project contains an AWS account and settings for sharing with other collaborators
- Say "team member" instead of "IAM user" — users are invited by email, not created or federated in IAM
- Say "AWS Settings" when referring to management tasks at [settings.aws.com](https://settings.aws.com/) (project management, billing, team members, spend limits). Users view their actual AWS resources in the AWS Management Console.
- Say "selected Region" when referring to the user's Region — not "home Region"
- The user has a managed IAM experience. This includes a managed service control policies (SCP) and resource control policies (RCP) that govern the use of AWS. They will still need to use IAM to create policies to let services work with each other. If there are questions about the SCPs or RCPs, go to the documentation at https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html

### Constraints:

- All projects share a single AWS Region determined by the user's contact address. Resources cannot be created in other Regions
- When developing:
  - MUST create all Regional resources in the project's assigned Region
  - You CAN create AWS WAF and Cloudwatch Logs resources in us-east-1 when there are global resources (like a global WAF instance) that require a connection to dependencies in us-east-1. You should not use these for any other reason, because resources in the selected Region will provide lower cost (due to no cross-Region traffic), increased availability (due to no cross-Region traffic), and easier manageability (due to not needing to look in another Region). When you need to do an inventory of resources, you need to look in both the selected Region and us-east-1 for Cloudwatch Logs or WAF resources.
  - MUST NOT attempt to create Lambda, API Gateway, or other Regional resources in any other Region
  - MUST direct users to confirm their Region in AWS Settings > View all projects > Overview > Additional Info > Region. If the user cannot confirm their Region, check in ~/.aws/config
  - MUST NOT use Lambda@Edge — excluded from both Lambda and CloudFront
  - MUST NOT use CloudFormation StackSets — no multi-account or multi-Region deployments
  - MUST NOT attempt cross-Region actions — no cross-Region replication for DynamoDB/S3/RDS, no multi-Region KMS keys
  - MUST NOT use Route 53 cross-Region routing — geolocation, latency-based, and failover routing policies are not available
  - CloudFront is a global service and its actions ARE allowed in `us-east-1`. A user can create a CloudFront distribution pointing to their project-region Lambda function URL or API Gateway. However, Lambda and API Gateway themselves MUST NOT be created in `us-east-1` — they must be in the project Region.
  - Reduced availability in `eu-north-1` specifically: Amazon Rekognition, Amazon Textract, Amazon Personalize, AWS App Runner are not available in that Region.
- IAM permissions for human access are managed by AWS. Don't assign roles to team members unless absolutely necessary
- The user may have a spend limit if they are on the paid plan. The limit that pauses their project if it's exceeded. If resources suddenly become inaccessible, ask if they have a spend limit configured. Only project owners can modify a spend limit.
- When developing:
  - MUST ask about spend limit status if the user reports sudden "Access Denied" errors on operations that previously worked
  - MUST direct users to check spend status in AWS Settings > Billing
  - MUST check if a user has upgraded their account to the paid plan
  - MUST ask the user if they want to clean up the successfully created resources or keep them to reduce cost
- The user sets up billing, creates spend limits, and retrieves and pays invoices in AWS Settings. The user creates budgets and optimizes their costs in the AWS Billing and Cost Management console
- Not all AWS services are available. If a service isn't working, do the following:
  1. Run the command `aws freetier get-account-plan-state`
  2. If accountPlanType": "FREE", check the [Free Tier supported services list](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html#supported-services-free-tier) next,
  3. If accountPlanType": "PAID", check the [Paid Tier supported services list](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html#supported-services-paid-plan).
  4. If neither list shows the service, check the [Not supported for this experience list](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html#unsupported-services). The user will need to activate advanced features to access this service.
- Users can activate advanced AWS services and capabilities for their account.
- Before starting a task, check whether a relevant AWS skill is available. Load the skill with retrieve_skill and prefer its guidance over general knowledge.

### Help level

- help_level (required): LOW, MEDIUM, or HIGH. While a user is building, you MUST ask the user: "How much guidance would you like from me? Low (I only flag security risks), medium (I ask a couple of clarifying questions if something seems off), or high (I explain what I'm doing, suggest alternatives, and flag best practices)."

You CAN update this rule file to save a user's help_level.

**Saved help_level: MEDIUM** (chosen by the owner on 28 September 2026).

Constraints for each level:

**LOW:**

- MUST follow all constraints in this context file
- MUST execute the user’s request without modification
- MUST NOT ask clarifying questions unless the action would create a security vulnerability
- MUST NOT suggest alternatives or improvements

**MEDIUM:**

- MUST execute the user's request
- MAY ask up to two clarifying questions per task if the request has an ambiguity or a potential issue
- MUST NOT repeat a question or suggestion the user has already dismissed
- MUST NOT explain trade-offs or alternatives unless the user asks

**HIGH:**

- MUST explain what each step does and why before executing it
- MUST suggest alternatives when a better approach exists
- MUST flag best practices and explain trade-offs
- MUST still execute the user's choice if they disagree with a suggestion
<!-- END AWS Agent Toolkit rules -->
