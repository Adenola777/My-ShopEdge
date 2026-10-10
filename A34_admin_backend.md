# A34. The admin backend

Written 10 October 2026, after the owner asked for an admin backend and answered two questions
the same day. **Approved by the owner on 10 October 2026**, with the four answers recorded in
A34.8. The facts it rests on were read from the repository on 10 October 2026 and are cited by
file and line.

## A34.1 What the owner chose

The owner chose all four parts offered for the first version:

1. **See everything.** Read-only views across every seller.
2. **Act on an account.** Suspend and reactivate, start a sync, retry a notice email, each
   written to an audit log.
3. **Data protection requests.** Find an account by email, build its export, and start or
   cancel its deletion.
4. **Business figures.** Sign-ups, trials, paying accounts and monthly revenue by plan.

For access, the owner chose an allow-list of email addresses, with the admin pages built as
their own Vercel project at their own address.

## A34.2 What exists today

- **Every request is scoped to one account.** `db.tenant()` sets the role `mse_app` and
  `app.account_id` (`service/app/db.py:69-75`), and row level security is forced on 28 tables
  (`schema/0003_force_row_level_security.sql`). No code reads across accounts except the
  thirteen SECURITY DEFINER functions, each of which does one narrow thing (0017 to 0031).
- **`mse_analytics` cannot read across accounts either.** It has no BYPASSRLS, and the tenant
  policies apply to every role (`schema/0001_roles_and_grants.sql:22`,
  `MyShopEdge_MVP_schema_v0.2.sql:432-486`).
- **Nothing sets an account to `suspended`.** The status exists and `require_account` refuses
  it with 403 `account_suspended` (`service/app/auth.py:307-310`), but no statement writes it.
- **`audit_log` exists and nothing writes to it.** It holds `account_id`, `actor`, `action`,
  `entity_type`, `entity_id` and `occurred_at`, it is append-only by trigger (0002), and its
  policy is `account_id = app_account_id()` (`MyShopEdge_MVP_schema_v0.2.sql:380, 480`).
- **The pieces the actions need already exist.**
  - A sync of one shop is `tiktok_sync.run_one(shop_id, account_id)` (`tiktok_sync.py:775`).
  - An account's export is built by `exports.build_account_export(account_id, export_id)`
    (`exports.py:477`), which takes any account id.
  - A deletion is the work `deleteMe` does (`account_deletion.py:138-187`), and the
    cancellation is the work `cancelAccountDeletion` does (`account_deletion.py:209`).

## A34.3 Who gets in

- **The allow-list.** A new variable, `ADMIN_EMAILS`, set on `My-ShopEdge-1` alone, holds the
  addresses separated by commas. When it is unset, every admin route answers 404, so a service
  that has not been given the variable exposes nothing.
- **The token.** An admin signs in with the same Stack sign-in a seller uses, and the token is
  verified the same way (ES256 against the fetched JWKS, `auth.py:238-288`). On top of that,
  `require_admin` requires three things:
  - the token is not a reviewer token (`auth.py:180-235`);
  - the provider's own record of the subject, `neon_auth.users_sync`, has
    `raw_json.primary_email_verified` true;
  - that record's email is on the list, compared in lower case.
- **Why the record and not the token.** The repository disagrees with itself about whether a
  Stack token carries `email` and `emailVerified`: `README_v0.2.md:64-65` says it does,
  `db.py:121-122` says managed tokens carry no custom claims, and A25 records the question as
  open. The synced record was queried on production on 10 October 2026 and holds both fields.
  Of 35 users, 29 were anonymous, 3 were verified and 3 were not. `inspirecraftglobal@gmail.com`
  and `adenola.adegbesan@gmail.com` were both verified.
- **What a refusal looks like.** Anyone else, signed in or not, gets the same 404 that a path
  which does not exist gives, so the admin routes do not announce themselves.
- **The routes.** Every admin route is under `/v1/admin/` and is documented in the contract
  under the tag Admin, because A13 rule 1 and the contract test require it.

## A34.4 How the service reads across accounts

**Proposed:** one SECURITY DEFINER function per admin view and per admin action, in a new
migration 0032, in the shape 0017 to 0031 set. Each is owned by `mse_migrator` and executable by
`mse_app` alone, and none of them is callable by `authenticated` or `anonymous`, which the
migration's closing check proves.

- **Why functions and not a role.** A role able to read every tenant's rows would be one grant
  away from every column, including the encrypted TikTok tokens. A function returns only the
  columns it names, so no admin view can return a token, a password or a card number.
- **What this does not protect against.** A fault in the service's own code could call these
  functions without an admin in the request, exactly as it could call `shops_due_for_sync()`
  today. The gate is `require_admin` in Python. That is the same standing the existing
  functions have.

## A34.5 What each part shows and does

**See everything** (read only)

| View | What it lists |
|---|---|
| Accounts | Email, status, created, deletion date, plan and plan status, number of shops |
| Shops | Shop name, code, account, connection status, last sync, the latest refresh failure code and message |
| Sync runs | The last runs per shop, with status, records read and written, and the error |
| Reconciliation | Per shop, how many statements reconcile and how many do not, from `settlement_totals_check` |
| Webhook log | Recent TikTok events, their type, shop and processing outcome |
| Notice emails | Counts by email status, and the failed ones with Resend's answer |

**Act on an account**

| Action | What it does |
|---|---|
| Suspend | Sets the status to `suspended`. The seller is then refused on every route (`auth.py:307-310`), and the daily sync skips the account, because `shops_due_for_sync()` lists active accounts only (0027) |
| Reactivate | Sets a suspended account back to `active` |
| Sync now | Runs `run_one` for one shop, in the background |
| Retry email | Sets a `failed` notice back to `pending` with no attempts, so the next sweep tries it again |

**Data protection requests**

| Action | What it does |
|---|---|
| Find by email | Returns the account that holds the address, or nothing |
| Build export | Runs `build_account_export` for that account and gives the admin the download link |
| Start deletion | Does what `deleteMe` does, on the seller's written request, with the 30 day wait A30.1 sets |
| Cancel deletion | Does what `cancelAccountDeletion` does, within the 30 days |

**Business figures**

All of these are read from `subscriptions` and `accounts`. Stripe remains the record of money
actually taken, so the page says that its revenue figure is the plans' list prices, not cash.

- Sign-ups by month.
- Accounts on trial.
- Paying accounts by plan.
- Monthly revenue by plan, from `price_minor` in `plans.py`.

**The audit log**

Every action writes one `audit_log` row with:

- the account;
- the admin's email as `actor`;
- the action's name;
- the entity it touched.

The log is append-only, so no admin can remove the record of what they did. Views are not
logged, because a log of every page load would bury the actions.

## A34.6 The admin site

- **Where it lives.** A new folder, `admin/`, holds a small Next.js app built and deployed as
  its own Vercel project. It signs in through the same Stack project and calls the same
  service through `NEXT_PUBLIC_API_BASE_URL`. It shares no build with the seller app, so a
  fault in one cannot ship the other.
- **The proposed address.** `admin.myshopedge.inspirecraftglobal.com`. The domain's DNS is on
  Namecheap, so the record is the owner's to add.

## A34.7 The order of work, one batch at a time

Each batch is shown to the owner and approved before the next starts.

1. **This ruling.** Approved, amended or refused by the owner.
2. **The service.** Four pieces go together:
   - migration 0032 with the functions;
   - `service/app/admin.py` with `require_admin` and the routes;
   - the contract additions;
   - a check against a local PostgreSQL 16 that proves a non-admin gets 404, an admin reads
     every account, and no view returns a token column.

   0032 is applied to the Neon branches only with the owner's authority.
3. **The admin site.** The `admin/` app, checked in a browser against the local service.
4. **Going live.** These steps are the owner's:
   - set `ADMIN_EMAILS` on `My-ShopEdge-1`;
   - add the admin address to `ALLOWED_ORIGINS`;
   - add it to Neon Auth's trusted domains;
   - add the DNS record on Namecheap;
   - approve the creation of the Vercel project.

## A34.8 The owner's rulings of 10 October 2026

1. **The allow-list holds the admin email.** The owner sets `ADMIN_EMAILS` on `My-ShopEdge-1`
   himself, so the address is not written into the repository.
2. **Suspending stops the plan renewing.** It uses the same call a deletion uses
   (`billing.set_renewal_for_deletion`), so renewal stops at the end of the period or trial
   under way, with no refund. Reactivating turns renewal back on only where the suspension
   stopped it, which is how cancelling a deletion behaves (A30.1).
3. **The seller is told.** A suspension writes a critical `account_suspended` notice and a
   reactivation an `account_reactivated` notice, and both are emailed (`notice_email`).
   **Derived, not ruled:** a seller who switched email notices off still receives no email,
   because NTF-2's acceptance reads "Opted-out sellers receive no email". The suspended
   seller can still read the notice's text in the email, but cannot open the notification
   centre, because a suspended account is refused on every route but getMe.
4. **An admin does not see a seller's money figures.** The admin views show counts of
   statements that reconcile and do not, and never a seller's sales, fees, payouts or ledger
   lines.

## A34.9 Where the build stands

**Batch 2, the service, was built on 10 October 2026.** It is unverified against Neon, Stack
and Stripe:

- `schema/0032_admin_views.sql` holds the seven read functions. It was applied with the
  owner's authority on 10 October 2026 to development, staging and production.
- `service/app/admin.py` holds `require_admin`, seven views and eight actions under
  `/v1/admin/`.
- The deletion steps moved into `account_deletion.close_account` and `cancel_closing`, so the
  seller's routes and the admin's share them.
- `notice_email` emails the two new notice types.
- The contract holds 87 operations across 75 paths.

What has run:

- `testdata/admin_check.py` passed 51 of 51 on a local PostgreSQL 16. It used stand-ins for
  Stack's verification, Resend and the sync.
- No account in it held a live Stripe subscription, so the Stripe half of suspension has not
  run.

**Batch 3, the admin site, was built on 10 October 2026** in `admin/`, a Next.js app on the same
`@stackframe/stack` 2.8.108 as the seller app. It has eight pages:

- an overview of the figures;
- accounts, with the email search and the actions;
- an account export's status;
- shops, with Sync now;
- sync runs;
- webhooks;
- notice emails, with Try again on a failed one;
- the audit log.

What has run:

- It lints, typechecks, passes `npm audit --omit=dev --audit-level=high` and builds, and CI
  runs the same in its own job.
- It was driven in Chromium against the real service on a local PostgreSQL 16. A scratch
  copy of the site stood in for Stack, and the service's `auth.verify` was replaced by a
  stand-in, so `require_admin` ran as written after verification.
- Signed out, it asks for sign-in. A verified address not on the list, and an unverified one,
  are each told the sign-in cannot open the admin pages.
- The admin saw the figures, found an account by email, suspended and reactivated it (both
  emails reached the stand-in for Resend), built an export and opened its status, and
  started a sync. The audit log listed each action under `admin:<email>`.
- At 390 px wide the page does not scroll sideways.

**Unverified:** a real Stack sign-in on the admin site. It needs the site's address on Neon
Auth's trusted domains, which is batch 4.

**Batch 4, going live, is in progress.**

- On 10 October 2026 the owner named `adenola.adegbesan@gmail.com` as the admin for now.
  This session set `ADMIN_EMAILS` to that address on `My-ShopEdge-1` through Render's API, on
  his instruction, and redeployed `ad73a6f`.
- The Vercel project, its address, `ALLOWED_ORIGINS` and Neon Auth's trusted domains are not
  done.
