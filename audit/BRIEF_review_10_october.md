# Review of the owner's audit and build brief, 10 October 2026

The owner uploaded `update.docx` on 10 October 2026 and asked for every part of it to be
reviewed. The brief has two halves: an audit brief (eight sections and a release gate) and a
build brief (22 sections plus the Stripe position). This file compares each requirement with
the repository and with production as they stood on 10 October 2026.

**How it was checked.** Four reviews read the code; three of them were run as separate
read-only agents, and every row they returned cites a file and line. Production figures were
queried on the production branch as `mse_migrator` the same morning. Nothing was changed in
the code, the database or any service. Where the repository cannot settle a point, the row
says so.

**Status words.** Pass: the code does what the brief asks. Needs change: the code does part of
it or does it differently. Missing: nothing exists. Conflicts with a ruling: the brief
contradicts a ruling document, so the ruling must be amended by the owner before the code can
follow the brief (A29.11). For the security and data rows the brief's own labels are used.

## 1. What production showed on 10 October 2026

| Query | Answer |
|---|---|
| Shops | 3, all connected: IkonetU and My ShopEdge on the owner's account, and **a third seller's shop, connected on 7 October by a second account** |
| Plans | The owner's account is trialing. The second account, which holds that shop, has **no plan**. Three further active accounts have no plan and no shop |
| Sync runs, last 7 days | 67 completed, 1 partial |
| Statements | 108 in `settlement_reconciliation`, 0 with an unexplained amount |

`shops_due_for_sync()` (`schema/0027_shops_due_for_sync.sql:24-32`) selects every active
account's connected GB shop and does not look at the plan. That shop is therefore read from
TikTok every day although its account has started no trial.

## 2. The findings that matter most

1. **Nothing in the service stops an account with no plan from seeing figures.** No route in
   `service/app` checks the subscription. The front end sends a seller with exactly one shop to
   `/billing` (`web/src/lib/onboarding.js:36`), but a seller with two shops is linked straight
   to Today (`web/src/app/shops/(list)/page.jsx:90`), and any shop address opens directly. The
   brief's billing access rule is the right fix, and the second account is the live case.
2. **No privacy notice, terms or cookie notice exists.** `web/src/app/(site)/start/page.jsx:12-15`
   records that neither page exists and that this must be closed before a real seller is
   invited. The landing page links to none. Vercel Analytics loads in the app
   (`web/src/app/layout.jsx:21`) with no consent step. A second seller is now connected. These
   need a qualified reviewer, not code alone.
3. **No per-shop validation report exists.** The 108 statements reconcile, which is strong
   evidence for payouts, but nothing compares sales basis, product figures or exports with
   TikTok's own figures in the format the brief asks for.
4. **Trial access is not taken from the Stripe webhook alone.** `start_trial` writes the trial
   from Stripe's API answer (`service/app/billing.py:196-199`). The webhook verifies its
   signature (`billing.py:468-476`) but stores no event id and does not check event order, so a
   late older event can overwrite newer state (`schema/0018_subscriptions.sql:93-103`). It
   handles four event types only (`billing.py:482-497`).
5. **A cost upload replaces existing costs without showing them.** Apply supersedes the current
   cost for every matched row (`service/app/cost_uploads.py:448-452`), dates every cost today
   whatever the file says (`:446, 458`), and offers no template.
6. **Retention is undefined.** The ledger retention period is open (`A30_rulings_28_september.md:25`),
   no `raw_events` purge exists in the service, expired export files stay in R2, and nothing
   says how long a shop with no plan is read and kept.
7. **Operations have no alerting.** A failed sync shows only in Render's job history. The
   erasure job fails every run until its variables are set. Token key rotation is not built.

## 3. Where the brief contradicts the rulings

A29.11 puts the owner's product decisions first. If the brief is a new decision, each ruling
below must be edited before any code changes; if it is not, the brief is wrong on these points.

| Brief | Ruling it contradicts |
|---|---|
| Sign-up form with name, email, password and confirm password | A14.3 rules a hand-off to the identity provider with no password field. Stack Auth has email and password off, and the owner cannot administer that Stack project |
| Stripe Checkout | The card is taken on MyShopEdge's own page with Stripe's Payment Element and a SetupIntent (`web/src/app/(site)/billing/PaymentForm.jsx`). The seller's outcome is the same: no charge today and a 30-day trial |
| Costs only after the first figures, then Overview | A14.2 puts costs and tax before Today, and skipping costs leads to the tax step (`setup/costs/page.jsx:24`) |
| Navigation Overview, Reconcile, Products, Returns, Stock, Exports, VAT and tax, Settings, with a More menu on mobile | A7.11 and the owner's rebuild of 7 October: five tabs, Today, Stock, Products, Money, Tax, with Settings in the top bar and More removed (`web/src/lib/nav.js:3-5`) |
| Titles Overview, Reconcile, VAT and tax | SCREENS.md registers S6 Today, S11 Money and S12 Tax |
| Net sales is gross sales less discounts less refunds | A8.4 and A8.5: net sales is gross less seller discounts, and refunds come after TikTok fees |
| Gross profit as the headline once costs are complete | A8.4: the headline is Gross profit after returns, shown with "before your own running costs and your tax" |
| Gross profit so far with partial costs | A4 and TC-RET-11: no profit figure is shown while coverage is incomplete |
| VAT and Export ready on the attention list | A29.6 fixes the item list and A29.8 keeps VAT out of Today |
| Red only for confirmed loss, green for complete, orange for selected states | A7.10 as amended on 24 September prints every deduction in red, keeps green, amber and red for payment status, and says orange never carries status |
| Six statuses: Reconciled, Awaiting settlement, Pending payment, Needs review, Unmatched, Sync delayed | A9.8 names the residual line Unexplained; only Awaiting settlement exists in the app |
| Cash basis by the date TikTok settled it | Not a ruling, but the ledger holds the settlement month only (`service/app/exports.py:237`) |

## 4. The landing page (`site/index.html`)

| Brief | What the page has | Status |
|---|---|---|
| Order: header, hero, problem, product costs, money, products, exports, returns, VAT and tax, stock, security, final CTA, footer | Hero, problem, security, how it works, then features in the order products, stock, returns, money, tax, then the final CTA | Needs change |
| Nav includes a working Pricing link | Why MyShopEdge, Security, How it works, Features, Sign in, Get started. There is no Pricing link and no price anywhere on the page | Missing |
| Hero heading "See what you actually keep from every TikTok Shop sale." | "See what your TikTok Shop really earns." | Needs change |
| Hero body names costs as optional | "works out your gross profit from them." The page never mentions product costs, so it promises gross profit without saying costs are needed | Needs change |
| Primary CTA "Start your free 30-day trial" | "Get started" | Needs change |
| Trust line under the hero | Absent; the security section says it later | Needs change |
| Hero screenshot shows the money lines | The Money screen with gross sales, seller discounts, net sales, five named fees and net proceeds before refunds | Pass |
| Screenshots use demo data, never a seller's | The product names (Vitamin C Serum 30ml, Lip Oil Trio) appear only in `A8_terminology_standard.md`, so the images are made-up examples rather than the demo shop | Pass, with that note |
| Problem section and worked breakdown | "TikTok pays you in pieces." with a breakdown from £62.00 to a £40.75 payout. "rarely matches what you sold" is calm | Pass |
| Product costs section (Excel, CSV, manual, optional, missing costs shown) | Absent | Missing |
| Exports section, including scheduled exports | Absent | Missing |
| VAT wording with the £90,000 figure and "not tax advice" | Names the threshold without the figure and has no disclaimer | Needs change |
| Security cards | Read-only, cannot place orders or touch money, encrypted, HTTPS, registered UK company, delete from Settings | Pass, subject to the scopes check in section 7 |
| Trial terms: card taken, nothing today, renews unless cancelled | "Start your free 30-day trial today." with no price, renewal or cancellation wording | Needs change |
| No "No card required" | Absent, correctly | Pass |
| Footer: privacy policy, terms, cookie policy, contact, company, ICO | Contact email, address, Companies House and ICO statement and badge. No privacy policy, terms or cookie policy | Missing |

## 5. Sign-up, connection, billing and costs

| Brief | What the code does | Status |
|---|---|---|
| Terms and privacy links on sign-up | None, because neither page exists (`start/page.jsx:12-15`) | Missing |
| Read-only reassurance before TikTok | On S1 Connect: "never changes anything in it", "What we read" and "Not kept" (`shops/(list)/page.jsx:53-79`). No encrypted or disconnect-anytime card | Needs change |
| Seller told about the redirect | "Opening TikTok Shop" and "You approve access on TikTok's own page" (`ConnectTikTok.jsx:50, 53`) | Pass |
| Import starts on connection | `_first_sync` runs as a background task (`service/app/connections.py:341-356`) | Pass |
| Import progress with no blank state and no percentage | Five parts marked Waiting, Reading or n found, with no percentage (`SyncProgress.jsx`) | Pass, steps differ |
| Straight into import after connection | The callback page asks for a click to continue (`connections/tiktok/callback/page.jsx:138-151`) | Needs change |
| Plan only after connection | `/billing` sends a seller with no shop to `/shops` (`billing/page.jsx:35`) | Pass |
| No figures, exports or core screens before a trial | See finding 1 | Missing |
| Price set by the server | The price id comes from the environment, never the browser (`billing.py:131-135`) | Pass |
| Trial only after a verified webhook | See finding 4 | Needs change |
| £0 today, renewal price, trial end date, cancellation before the card | Price a month after the trial, the trial end date, "charge nothing today", "stop the plan in Settings" (`PaymentForm.jsx`). Not the literal "£0 due today" or "Cancel before [date]" | Needs change |
| Success page with the renewal terms and a next step | "Your free trial has started." without the renewal price; its button goes to `/shops` | Needs change |
| Abandoned card step: "No changes were made", resume, disconnect | The plans are shown again with none of those | Needs change |
| Connected but no plan: Start trial and Disconnect together | On two separate Settings pages | Needs change |
| Disconnect shop | `disconnectShop` marks tokens revoked and keeps data; TikTok is not told (`connections.py:538-580`) | Pass, partly |
| Failed payment grace period | Read access is kept (A14 S38); no length is defined | Missing |
| Cancelled or expired account state | "Your plan has ended." The service refuses nothing, and a cancelled account can start a second trial, which no ruling covers (`billing.py:40-43`) | Needs change |
| Billing status in Settings | Plan, status, next date and controls (`settings/profile/page.jsx`). The card's last four digits are always empty | Pass |
| Billing portal and invoices | No portal and no invoice list | Missing |
| Trial reminder | No `trial_will_end` handling; the app relies on Stripe's own email, whose setting the repository cannot show | Not verifiable |
| First result screen with the waterfall | None; the first figures are Today | Missing |
| Cost choice with a real skip | Exists, but skip leads to the tax step (A14.2) | Conflicts with a ruling |
| Cost upload: template, preview, five statuses, no silent overwrite, file dates | Matched, unmatched and duplicate only; see finding 5 | Needs change |
| Manual partial entry | Rows ordered by units sold, each saved on its own | Pass |
| Gross profit reveal with cost coverage | None | Missing |

## 6. The app screens

| Brief | What the app does | Status |
|---|---|---|
| Missing cost never shown as £0.00 | The service returns null with a reason and the app shows "Not known" (`money_view.py:270-297`, `Figure.jsx:33-40`); exports write a blank (`exports.py:127`) | Pass |
| No "profit" before costs | Today says "This is net proceeds…" when costs are missing, but its month card is still titled "Gross profit after returns this month" and reads "Not known" (`today/page.jsx:150-154`) | Needs change |
| Cost coverage shown | The service sends `cost_coverage` (`money_view.py:201-204`); only Settings and manual entry show it | Missing on Today, Money and Products |
| Period selector and one primary figure | Today shows a single day's figure beside two month cards; there is no period selector on Today | Needs change |
| Every figure drills down | Every Money line links to Records; Today's figures do not | Needs change |
| Attention list, at most five, calm wording | Up to 14 item types with no cap (`today_view.py:316-321`); chips read Act now, Check and Note | Needs change |
| Last updated | "Updated 09:12" in the top bar on every screen (`AppBar.jsx:66-73`) | Pass |
| Sales and cash basis kept across screens | Only Money has the switch, held in its address | Needs change |
| Explain a payout in two clicks | Two clicks from Money, three from Today. The detail shows fees, reserve and unexplained, but only a count of orders, not the orders | Needs change |
| Products: coverage card, template, table, cost statuses | One figure per product, ranked by gross profit after returns; uncosted products listed below with net proceeds | Needs change |
| Returns: wording, confirmation before Unsellable, no double counting | Resellable, Unsellable and Nothing came back with a preview before recording; the service refuses a second check with 409 (`returns.py:367`). Checked returns cannot be seen again | Pass on double counting, needs change on the rest |
| Stock figures | On hand, days of cover, sold not dispatched, returns in transit, written off, per variant. No totals and no "runs out first" | Needs change |
| Exports: types, periods, basis, Excel and CSV | All present in the brief's order (`SetupForms.jsx:530-618`) | Pass |
| Export confirmation sentence | Names Money rather than Overview, month summary only | Needs change |
| Scheduled exports | Type, format, basis, cadence, day, active or paused; no next run date | Needs change |
| VAT: rolling twelve months, £90,000 dated | Twelve London months of gross sales against `reference_rules`; the threshold's date is served but not shown | Needs change |
| Tax reserve with missing costs | "Not known" with a reason and "Add costs"; "It is not tax advice."; a limited company sees no figure | Pass |
| Settings: connection, disconnect, notifications, plan, data, delete | All present; deletion asks for the account email to be typed | Pass |
| Privacy and support contacts in the app | None | Missing |

## 7. Data, calculations and security

| Brief | Evidence | Status |
|---|---|---|
| One calculation layer | `money_view.calculate` feeds Today, exports, trends and tax; `insights.py` reads the products query directly | Partially implemented |
| Gross margin | Not computed anywhere in `service/app`, so the brief's denominator cannot be audited | Missing |
| Unknown TikTok fee | Posted as `unmapped_fee` and shown under TikTok's own name (`tiktok_sync.py:400-408`, `money_lines.py:26-40`) | Implemented but evidence not reviewed |
| Integer pence through `Decimal` | `money.py`; fault 7 in CLAUDE.md | Implemented and verified |
| Duplicates | Every insert is `on conflict`; a second run writes nothing new | Implemented and verified on generated data |
| Payout to statement | 108 statements, 0 unexplained on production | Implemented and verified |
| Audit trail | Ledger, change log and audit log are append-only by trigger (0002); the 9 October correction added rows and changed none | Implemented and verified |
| Export parity | The month summary comes from `calculate`; run against the local copy only | Implemented but evidence not reviewed |
| Per-shop validation reports | None | Missing |
| Tenant isolation | Forced row level security, `security_invoker` views, fault 1's leak proof and fix | Implemented and verified |
| Read-only TikTok scopes | `granted_scopes` is stored, but A24 records the minimal set as never checked, and Inventory Search needs `seller.product.basic` | Partially implemented |
| Token encryption | AES-GCM with `TIKTOK_TOKEN_KEY`; rotation not built | Partially implemented |
| Staff access logged | Every admin action writes `audit_log`; admin views of seller data are not logged, by A34.5 | Partially implemented |
| Demo data fictional and on development only | `testdata/load_demo.py` | Implemented but evidence not reviewed |
| Webhooks | TikTok signed and de-duplicated, 27 of 27 tests; Stripe signed, see finding 4 | TikTok verified; Stripe partly |
| No card data held | SetupIntent in the browser; only Stripe references are stored | Implemented but evidence not reviewed |
| Retention, incident response, backups | None documented; backup retention is listed as open in README_v0.2.md | Missing |
| Privacy policy, terms, cookies | None | Missing; requires legal review |
| Daily sync | 67 completed and 1 partial in seven days | Implemented and verified |
| Seller refresh with a rate limit | None; only the admin can start a sync | Missing |
| Monitoring and alerts | Render job history only | Missing |
| No raw errors shown | A global handler answers "Something went wrong at our end." | Implemented but evidence not reviewed |

## 8. Release decision under the brief's own gate

The brief allows four decisions. On this evidence the supported one is **"Not ready to expand
beyond private beta"**: payouts reconcile and isolation is proven, but the gate's own
conditions on validation reports, legal documents, billing access and monitoring are not met.
