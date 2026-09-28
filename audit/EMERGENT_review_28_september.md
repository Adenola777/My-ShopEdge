# Emergent AI's work, reviewed 28 September 2026

## What exists

Emergent AI worked on a copy of this repository, not on this repository. The copy is
`Adenola777/MYSHOPEDGE`, which is public. Its history is this repository's up to `c47e6f4`,
the merge of PR 9 on 25 September, followed by 14 commits by
`emergent-agent-e1 <github@emergent.sh>` on 25 and 27 September. Its `main` ends at
`d87f6a0`. The zip the owner uploaded on 28 September, `MYSHOPEDGE-main_1.zip`, is that
commit exactly, checked file by file.

`Adenola777/My-ShopEdge` holds no Emergent commit, and Render deploys from it (read from
Render's configuration on 28 September). None of Emergent's work is live.

| Date | Commit | What it did |
|---|---|---|
| 25 Sep | `06faeba` | Wired Stripe billing to the database |
| 25 Sep | `885618f`, `f11b835` | A local database harness, a QA token, billing tests, `memory/test_credentials.md` |
| 25 Sep | `91aeed4` | Tax: profile, VAT threshold monitor, set-aside, dates, quarterly check |
| 25 to 27 Sep | `73b135f`, `728b1c7`, `9980785`, `5218e62` | Emergent's platform files, and the deletion of both `.env.example` files |
| 27 Sep | `4d45b15`, `845a6df` | Committed a PostgreSQL data folder of 1,488 files, then deleted it. It stays in that history |
| 27 Sep | `3f1bd43`, `972d324`, `caa5b68` | Exports, file storage, cost uploads and nine screens |
| 27 Sep | `d87f6a0` | Cost changes to `costs.py`, `me.py` and `products.py` |

**Credentials.** gitleaks over the whole history found one item, a signed token in
`scripts/qa/tok_a`. Its issuer is `qa-issuer` and its audience `qa-aud`, so it is a local
test token that the live service refuses. No private key, Stripe key or database password
appears. Emergent's PRD dates its own work 25 and 26 June 2026, which is three months wrong.

**Emergent's claims against this repository's checks.** Emergent reported every suite
passing. Run against this repository's own checks, the zip fails the contract test ("served
but not in the contract: `/me/export/{exportId}/download`") and fails lint with 9 errors,
one of which is `date.today()` in `rules.py` against the London business date rule (A29.9).

## Verdict on every change

The owner approved on 28 September bringing Emergent's useful work into this repository.
Each change was read in full and judged as follows. **Nothing has been brought across yet**:
the step that copies the files was refused by this session's safety check, and the owner
decides how to proceed.

### Worth taking

| Change | Note |
|---|---|
| `billing.py`, `db.py`: Stripe wired to the database, `GET /billing/subscription` | Closes most of audit finding H2. Writes go only through the SECURITY DEFINER functions of migration 0018. One gap remains: a second trial request still creates a second subscription at Stripe |
| `connections.py`: `DELETE /shops/{shopId}/connection` | Sound. It marks the stored TikTok tokens revoked and leaves them stored, encrypted, which needs checking against the data protection document |
| `money_view.py`: month summary and where it went | Sound. Remove the unused `Problem` import that fails lint |
| `settlements.py`: record a settlement's invoice number | Sound. The optional gross, net and VAT are accepted and not stored, and the code says so |
| `stock.py`: velocity | Sound, with one note: its net proceeds leaves out platform adjustments, which Money counts in |
| `tax.py` with `testdata/reference_rules_tax_seed.sql`, and the Tax screen | No Emergent dependency. The wireframe makes Tax the fifth tab |
| `other_sales.py` and its screen | No Emergent dependency |
| `alert_settings.py` and its screen | No Emergent dependency |
| `rules.py` with `testdata/reference_rules_seed.sql`, and the Glossary screen | Replace `date.today()` with `business_today()` |
| Screen S16 Product transactions, and the link to it from product detail | Passes lint and the type check |
| `.gitignore` additions | Excludes `.pgdata/`, logs and credential files |

### Worth taking once fixed

| Change | Fault |
|---|---|
| `products.py`, `costs.py`: the cost in force at the period's end | Matches the contract, which says a new cost must not rewrite past months. A same-day correction leaves two rows with one `effective_from`, and the query then picks either. Order by `created_at desc` as the tie-break |
| Screen S28 Connection problem | Handles `error` and `expired`, which the schema never holds, and misses `needs_reconnect`, the real case. One type error |
| Screen S2 First sync, `SyncProgress.jsx` | Shows raw status codes where A8 requires plain words, uses chip styles the stylesheet lacks, prints server time rather than London time, and has 7 type errors that would fail CI |
| `ShopNav.jsx` | Adds Tax and Settings tabs. MSE-WFW-001 section 1.1 specifies five tabs, ending with Tax. Take Tax, and reach Settings from the top bar |
| Settings hub and `SettingsForms.jsx` | Keep alert settings and disconnect. Remove delete and export, below |

### Not taken

| Change | Reason |
|---|---|
| `DELETE /me` | A soft delete that erases nothing, while its reply tells the seller the deletion "includes" their orders, ledger and costs. What erasure removes under an append-only ledger is a data protection ruling for the owner |
| `storage.py`, exports, cost uploads, the account data download | They store files with Emergent's own service at `integrations.emergentagent.com` under an Emergent key. They cannot work on Render, and they would send seller files to a processor no document names. A10.8's storage decision stays open |
| `stack.js` `NEXT_PUBLIC_DEV_BEARER` | A public build variable carrying a bearer token. Set in production, it would sign every visitor in as one seller |
| `api.js` internal base URL, `backend/`, `frontend/`, `.emergent/`, `.gitconfig`, `scripts/`, `memory/`, `test_reports/` | Emergent's preview environment and notes, not the product |
| Deleting `service/.env.example` and `web/.env.example` | They are the only record of which settings the service needs |
| Emergent's pytest suites | They call a running preview URL with a stored token, so they cannot run in this repository's CI |
