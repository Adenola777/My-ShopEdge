# A36. Aligning the web app with the owner's brief

Written 10 October 2026. The owner's `update.docx` (an audit brief and a build brief) was
reviewed that morning in `audit/BRIEF_review_10_october.md`, whose section 3 lists where the
brief contradicts earlier rulings. The same afternoon the owner ruled on each conflict and then
answered five open questions. This file records both, and where a ruling below conflicts with
an earlier one, this file wins for the point it names (A29.11).

## A36.1 The owner's rulings

| # | Subject | Ruling | Replaces |
|---|---|---|---|
| 1 | Sign-up | Keep sign-in through Stack with Google. No password form | Nothing; A14.3 stands |
| 2 | Card | Keep the card form on MyShopEdge's own page (Stripe Payment Element and a SetupIntent), not Stripe Checkout | Nothing; the billing flow stands |
| 3 | Setup order | The brief's order: first figures, then the optional cost choice. Where no cost is uploaded, the brief's rules apply | A14.2 (costs and tax before Today) |
| 4 | Navigation | The brief's eight areas in its order: Overview, Reconcile, Products, Returns, Stock, Exports, VAT and tax, Settings. A sidebar on a desktop; on a phone, Overview, Reconcile, Products, Exports and More | A7.11 (five tabs) |
| 5 | Net sales | Gross sales less seller discounts less refunds | A8.4 and A8.5 order |
| 6 | Partial costs | "Gross profit so far", shown with cost coverage | A4 and TC-RET-11 |
| 7 | Colours | Keep MyShopEdge's colours, improve them where needed, and ask the owner where unsure | A7.10 stands, amended item by item |
| 8 | Payout statuses | Reconciled, Awaiting settlement, Pending payment, Needs review, Unmatched, Sync delayed | A9.8's single "Unexplained" state |
| 9 | Plan before figures | The brief's billing access rule. The accounts without a plan are test accounts | A35.1 item 2 ("Everything, as today") |

## A36.2 The owner's answers to the open questions

1. **Gross profit so far** counts the products that have a cost only, with cost coverage beside
   it. Uncosted products are not added in at full net proceeds.
2. **Unmatched** is a payout with no statement behind it. **Sync delayed** is a payout read that
   failed or is more than a day old.
3. **Deductions** are shown in dark text with a minus sign. Red is kept for write-offs, failed
   payments and unexplained differences.
4. **An ended plan** (cancelled or expired) keeps its figures readable, with no exports and no
   new syncs.
5. **A shop whose account never starts a trial** is read for 30 days from its connection, then
   no more, and its data is deleted. The Privacy Policy must say the same.

## A36.3 Built in step 1, 10 October 2026

- **Access by account state** (`service/app/entitlements.py`, `access_for_row` and
  `shop_access`, called from `shops.require_shop`).
  - With no trial, every shop route answers 403 `trial_required`. The exceptions are the
    import's progress (`GET /sync`), disconnecting (`DELETE /connection`) and the alert
    settings.
  - With an ended plan, reading carries on. Any write and any export answers 403
    `plan_ended`.
  - The features of an ended plan are those of the plan it last held, less the three export
    features. An account with no trial holds none.
- **Reading TikTok** (`tiktok_sync.may_sync`, used by the daily run and by the webhook's
  scoped sync).
  - An account with a live plan is read as before.
  - An ended plan is not read again.
  - An account with no trial is read for 30 days from the shop's `created_at`.
- **The Stripe webhook** reads each subscription back from Stripe before writing it, so a
  late, older event cannot undo a newer one. It logs every event's id and type.
  **Unverified against Stripe**: only the live account is reachable, so this has run
  against a stand-in only.
- **The app.**
  - `trial_required` takes the seller to the plan page. That page now names the
    connected shop, says "Connected, trial not started" and "We are preparing your shop
    figures while you choose your plan.", and offers Disconnect.
  - Settings shows the same state, with "Start 30-day free trial".
  - `plan_ended` explains that the figures can still be read, with "Choose a plan".

Trial state is written only by the service: from Stripe's webhook, or from Stripe's own
answer when the service asks it (on starting the trial, and on reading back an incomplete
row). The browser never sets it.

## A36.4 Built in step 2, 10 October 2026

- **After TikTok approves.** The callback page sends a connected shop straight to its import,
  with no extra click. The import page names the shop and says it is connected.
- **The import page.** It follows the brief's section 5: "We are putting your figures
  together.", the four steps worked out from the sync status, and "We will show your first
  results as soon as they are ready." There is no percentage. With no trial, its button is
  "Choose your plan".
- **The trial active page.** The brief's "Your 30-day trial is active.", with the trial end,
  the plan and its renewal price. Its button is "See my shop figures" once the import has
  finished, or "Prepare my shop figures" while it runs. A trial started without a bank
  redirect now goes to the same page.
- **An unfinished card step.** The plan page says "No changes were made. Your TikTok Shop is
  connected, and you can start your 30-day trial whenever you are ready."
- **The first reconciliation.**
  - `/shops/{id}/first-result`, for the last 30 London days, with the brief's heading,
    definition and reassurance.
  - "Explore my figures" and "Add product costs".
  - Lines and subtotals come from `getMoney` as served, so refunds move above net sales when
    step 3 changes the service.
- **The cost choice.** The brief's wording, with Skip leading to Overview. Starter sees the
  Growth prompt here.
- **The gross profit reveal.**
  - `/shops/{id}/profit-reveal` shows gross profit, margin and cost coverage, and the products
    still missing a cost.
  - Manual entry offers "Save costs and see gross profit" and "Save and continue later".
  - A finished upload links to the reveal.
  - The brief's "share of sales value" wording waits for step 3.
- **Onboarding order.** A seller with a plan goes to Overview. Costs and tax no longer come
  first (A36.1 item 3).

**Unverified**: the trial active page has run against the local copy only, where the demo
shop has no import records, so "See my shop figures" has not been seen on screen.

## A36.5 Built in step 3, 10 October 2026

- **Net sales** (`money_view.CHAIN`). The first section is Sales: gross sales, seller discounts
  and refunds to customers, with Net sales as its subtotal. The TikTok fees section ends at Net
  proceeds, and the separate refunds stage is gone. Net proceeds come to the same figure. The
  product ranking, product detail and insights use the same definition. A8.5 is amended.
- **Gross profit so far** (`Totals.gross_profit_so_far`, and the Overview month). When some
  sold products lack a cost, it is the sum of gross profit after returns over the costed
  products. It is null when every product has a cost, because gross profit after returns is
  then shown, and null on Starter.
- **Cost coverage by sales value** (`CostCoverageBySales`, served on `getMoney`, `getToday`'s
  month and `getProducts`). It carries the costed share of net sales, the count of products
  missing a cost and their net sales.
- **The screens.** Overview, Where the money went, Products and the gross profit reveal show
  "Gross profit so far" with the sentence "Based on product costs for X% of sales value. Costs
  are still missing for N products affecting £Y of sales." and a link to the missing costs.
  The first reconciliation shows the Sales and TikTok fees sections only.

Checked on the local copy of the showcase shop, in the browser and through the service. With every cost present, net
sales read £6,428.00 (they read £7,130.00 before), net proceeds stayed at £5,668.77, and gross
margin read 52.7% (47.5% before), because the denominator lost the refunds. With the Computer
Desk's costs set aside, gross profit so far read £2,660.07, equal to the sum of the costed
products' gross profit after returns, and coverage read 73.9% with 1 product and £1,675.00 of
sales missing, the same on Money and Products.

## A36.6 Built in step 4, 10 October 2026

- **The map** (`web/src/lib/nav.js`). The eight areas are in the brief's order: Overview,
  Reconcile, Products, Returns, Stock, Exports, VAT and tax, and Settings. Returns and Stock
  were one area until now, and Exports was a page of Reconcile. No page address changed.
- **A larger screen.** The sidebar lists all eight, with Settings at its foot. The area in
  use opens to list its pages.
- **A phone.** The bottom tabs are Overview, Reconcile, Products, Exports and More. The new
  More page (`/shops/{id}/more`) lists Returns, Stock, VAT and tax, Notifications, Settings,
  Help and glossary, and Sign out. More is marked while the seller is on it or on any area it
  holds.
- **The top bar** keeps the Updated stamp and the bell. The Settings gear is removed, because
  Settings is now in the sidebar and on More.
- **Back links.** Returns no longer points back to Stock, and Exports no longer points back to
  Where the money went, because each is now an area of its own.
- **The glossary**, which step 3 missed, now defines net sales as gross sales less seller
  discounts and less refunds, and adds Gross profit so far.

Checked in a browser on the local copy at 390 and 1280 pixels wide, on ten pages. Each page
marked the right area, the phone showed the five tabs, the sidebar showed the eight, and no
page scrolled sideways.

## A36.7 Built in step 5, 10 October 2026

The owner approved steps 5 to 8 together on 10 October 2026. Step 5 follows the brief's
sections 11 and 12, read from `update.docx`.

- **The payout status** (`settlements.payout_status`). Each statement carries one payment, so a
  payout is a statement and its payment. The service serves `reconcile_status` and `difference`
  on listSettlements and getSettlement:
  - Reconciled: TikTok paid it, and the orders behind it add up to it.
  - Pending payment: TikTok has issued it and not paid it.
  - Needs review: the orders do not add up to it, or TikTok reports the payment failed.
  - Sync delayed: it is not paid, and the last read of the shop's statements failed or is more
    than a day old. A paid statement is final and is never Sync delayed.
  - Awaiting settlement belongs to orders not yet on a statement. Payouts shows TikTok's
    expected payouts under it.
  - **Unmatched is never given.** MyShopEdge reads payouts only as part of statements, so it
    holds no payout without one. Reading TikTok's own list of payments would be needed, and it
    is not built.
- **Reconcile** opens on Payouts, with the brief's title and subtitle. Its tabs are Payouts,
  Where the money went, Transactions and Issues. Issues is the discrepancy list, moved from
  Overview. **The brief names a Statements tab.** TikTok pays each statement once, so a
  separate Statements list would repeat Payouts row for row. Each payout row names its linked
  statement instead. Each row shows the payout date, the payout amount, the linked statement,
  the status and the difference. What TikTok has paid and still owes, the Shop Money card,
  moved from Overview to the top of Payouts.
- **Explain this payout** shows:
  - the payout received, the status, the linked statement and the difference;
  - a plain sentence on what the status means;
  - the statement's fee lines, shipping, adjustments and reserve;
  - the included orders, and a pointer to Awaiting settlement;
  - when TikTok issued and paid the statement, and when MyShopEdge last read it
    (`finance_read_at`).

  Refunds are not a separate line, because TikTok's statement does not state them on their own.
- **Overview** has these parts:
  - the brief's controls: today, this month or last month; the sales or cash basis; the
    export; and the time of the last update. No refresh is offered, because the daily read
    cannot be started from the app.
  - one primary answer, which follows the period's cost coverage. With every cost it is gross
    profit after returns with the margin, keeping A8's label. With some costs it is gross
    profit so far with the coverage sentence. With none it is net proceeds with the brief's
    definition.
  - the full calculation under "Where the money went".
  - "What needs your attention", which the service caps at five items. It now includes
    "Payout needs review", and when the list is empty it reads "You are up to date".

Checked on the local copy at 390 and 1280 pixels wide. Fifteen statements read Reconciled. One
statement, not yet paid on a shop with no recorded read of TikTok's statements, read Sync
delayed. TikTok's expected payouts were not shown, because the local copy cannot reach TikTok.
**Unverified on production**: Needs review has run in the smoke test only, because the local
copy has no statement with a difference.

## A36.8 Built in step 6, 10 October 2026

Step 6 follows sections 13 to 17 of the brief.

- **Products**
  - The page has the brief's subtitle and names the measure the ranking uses.
  - The brief's table is served by `listProducts`. It shows the product, units sold, net
    sales, TikTok deductions, product cost, return impact, gross profit after returns, gross
    margin and cost status. Starter's table stops at net proceeds.
  - The cost status is Complete, Cost needed or Partially costed, from the variants sold
    (`products.cost_status`). Needs review is in the contract for a cost an upload cannot
    match with certainty, which step 7 handles. It is not given yet.
  - The product page adds net proceeds and the cost status, and names "Edit product cost".
  - A fault found on the way was fixed: the product page called every fee one MyShopEdge
    does not recognise. It now marks only the fees Money marks.
- **Returns**
  - The page has the brief's title and subtitle, and shows the items awaiting inspection.
  - It shows the items already checked, read only, as Resellable, Unsellable and written off,
    or Nothing came back, with what each did.
  - The brief's wording for each choice is on the form, and Unsellable asks for a second
    press before it records.
  - **The optional note is not built**, because the service has nowhere to keep one.
- **Stock**
  - The page has the brief's subtitle.
  - It shows the whole shop's units in hand, sold but not posted, coming back and written off.
  - It lists the three variants still in stock with the fewest days of cover. `getStock`
    serves both on its first page.
  - The brief's "add costs to see profit contribution" is not shown, because no stock figure
    is costed.
- **Exports**
  - The page has the brief's subtitle, and the cash basis is worded as the day TikTok settled
    it.
  - The confirmation reads "This export covers ... on the ... basis".
  - Each scheduled export shows its next run (`next_run_on`).
- **VAT and tax**
  - The page has the brief's subtitle.
  - The VAT card shows the rolling twelve-month turnover, this month's sales, the threshold
    with the date it was checked against gov.uk, and the amount remaining.
  - It shows a progress bar from the service's `share_of_threshold` and the time the figures
    were worked out. Its wording is calm and does not state a legal duty.
  - With costs missing, the tax card shows the brief's heading and copy. It always carries the
    brief's disclaimer.
  - **"Approaching" is not shown**, because no ruling says at what share of the threshold it
    begins. It needs the owner's figure.

Checked on the local copy at 390 and 1280 pixels wide, with no page scrolling sideways. On
every one of the six products, net sales plus TikTok deductions equalled net proceeds, and net
proceeds, product cost and return impact added up to gross profit after returns.

## A36.9 Built in step 7, 10 October 2026

Step 7 follows section 8A of the brief.

- **The template.** "Download cost template", on the upload page and on Products, gives a CSV
  of every variant in the shop with the cost in force today. Its columns are SKU, product,
  variation, cost per unit and effective date. It is laid out by the web app from
  `listSkuCosts` and works nothing out. A variant with no seller SKU carries TikTok's SKU id,
  which Excel shortens unless the column is formatted as text, and the page says so.
- **The upload page** has the brief's heading and body, the expected columns, and a drop area
  that also opens the file chooser.
- **Each row takes one of the brief's five statuses** (`cost_files.match`):
  - Matched: it sets a cost where none is in force on its date, or the same cost.
  - Needs review: a different cost is already in force on its date, and the row carries
    that cost.
  - No match found.
  - Duplicate: the same variant and date appear earlier in the file.
  - Invalid cost: the amount or the date cannot be read.
- **No silent overwrite.** A Needs review row is applied only when the seller ticks "Replace"
  beside the cost it would replace.
- **The preview table.** Before anything is saved, the table shows each row's imported code,
  the matched TikTok product and variation, the SKU, the cost per unit, the effective date
  and the status. It also shows how many rows are ready to apply and how many need review.
  The button reads "Apply costs to N products", "Review unmatched products" lists the rest,
  and the page says "You can edit or replace costs later."
- **Dates in the file are used.** An optional effective date column is read from an Excel
  date or as text such as 2026-08-01 or 01/08/2026, day first. Each cost applies from its
  row's date, or from today when the row has none. Two rows for one variant with different
  dates are both kept.

The contract's `unmatched` outcome is now `no_match` and `invalid_cost`. `rows_unmatched`
stays, as their sum, and a match stored before this change is read as before.

Checked on the local copy with a local stand-in for the file store. A seven-row file gave:
- one Matched;
- two Needs review, with the cost already set beside them;
- one No match found;
- two Invalid cost, one amount and one date;
- one Duplicate.

Applying wrote each chosen cost from its own date, or from today. The local cost tables were
restored afterwards. **Not checked in a browser**, because the local service does not allow
the browser's writes across origins. The cost status Needs review on Products is still not
given, because a seller's choice in the upload is not kept against the product.

## A36.10 Built in step 8, 10 October 2026

Step 8 follows section 18 of the brief, adds the app footer's links, and applies the colour
ruling the owner approved (A36.2 item 3).

- **Settings, in the brief's order.** The pages are TikTok Shop connection, Notification
  settings, Account, billing and plan, Data and privacy, Delete account, Your shops, and Help
  and glossary. Product costs stay under Products, and the connection page links to them.
- **The connection page** opens with the brief's sentence: "MyShopEdge can read your TikTok
  Shop data but cannot place orders, issue refunds or change your shop." It shows the status,
  the last sync, Data sync, Reconnect and Disconnect.
- **Data and privacy** says how long each kind of data is kept, in the Privacy Policy's own
  periods, and links to the policy. It offers Delete account, which asks for the account's
  email to be typed and can be cancelled for thirty days. It names the privacy and support
  contacts, and keeps the data download.
- **The app footer** links to the Privacy Policy, the Terms and Conditions and the Cookie
  Policy, with the support and privacy addresses the product site publishes.
- **Colours.**
  - A deduction is now dark text with its minus sign.
  - Red is kept for stock written off, for differences nobody has explained, and for Needs
    review, which covers a failed payment.
  - No colour token changed, and no other colour change was made.

**One mismatch for the owner.** The Privacy Policy says a seller can download their data
"under Settings, Your data". That page is now called Data and privacy. The policy is the owner's
document, so it was not edited.

Checked in a browser on the local copy at 390 and 1280 pixels wide, with no page scrolling
sideways.

## A36.11 Still to build

Deleting the data of a shop whose account never starts a trial, 30 days after connection, is
not built. It removes data, so it needs the owner's approval of the job before it runs, and the
Privacy Policy needs the same period.

## A36.12 The owner's choices of 11 October 2026, and item 4 built

On 11 October 2026 the owner chose to build three of the remaining items, the optional note on a
return check, Needs review as a product's cost status, and Unmatched payouts, in that order. He
agreed that Reconcile keeps no separate Statements tab, for the reason A36.7 gives: TikTok pays
each statement once, so the list would repeat Payouts row for row.

**Item 4, the optional note on a return check (section 14 of the brief).**

- Migration 0033 adds `return_items.seller_note`, null when the seller wrote nothing, and at
  most 500 characters. **The bound is derived, not ruled**: the brief sets no length.
- `checkReturnItem` takes `seller_note`. Spaces alone count as no note, and a longer note is
  refused with its length. The note is written with the check, and a check is one way, so a
  note is never edited.
- `listReturns` serves each item's note, and the Returns page shows it on a checked item as
  "Your note".
- The form offers "Note (optional)" once a choice is made.
- **Safe before 0033 is applied.** The list reads every note as null while the column is
  missing, and a check that carries a note answers 503 `migration_pending` and records nothing.
  A check without a note works as before.

Checked on 11 October 2026:
- The smoke test covers a note kept, a note of spaces dropped, and a note of 501 characters
  refused.
- On a copy of the local demo database, 9 of 9 passed: before 0033 the list answered with
  every note null, and a check with a note answered 503 and recorded nothing. After 0033 the
  check kept the trimmed note, the list showed it, a second check was refused, and the column
  refused 501 characters and an empty note.
- `migrate.py` built a database from empty with 0033.
- In a browser at 390 and 1280 pixels wide, the field appeared after a choice, held at most 500
  characters, and a checked item showed its note, with no page scrolling sideways. The check
  was not recorded from the browser, because the local service does not allow the browser's
  writes across origins.

**0033 was applied on 11 October 2026**, with the owner's authority, to development, staging and production, each in one transaction with its record and checksum. Queried afterwards, the column exists on all three.

## A36.13 Item 5 built: Needs review as a product's cost status, 11 October 2026

Section 8B of the brief lists four cost statuses for a product, and Needs review was the one
not given. It is now given.

**When a product needs review. Derived, not ruled**; the brief names the status only. A
product needs review while one of its variants meets all three of these:
- the shop's latest cost upload has been matched and not applied;
- that match found a cost for the variant different from the cost in force, which is the
  upload's own Needs review (A36.9);
- no cost has been set for the variant since the match.

Applying the upload settles it, whether the seller replaced the cost or kept it. So does a
newer upload, or a cost set by hand on the product page. Needs review comes before the other
three statuses, because it asks the seller to decide something.

- Migration 0034 adds `cost_upload_reviews`, one row per variant per upload, with row level
  security on the shop's account. `matchCostUpload` writes the rows and `applyCostUpload`
  clears them.
- `listProducts` and `getProduct` give `needs_review`. The contract's description says when.
- The product page explains what the latest file found, says nothing has changed, and links
  to the upload. The web app cannot reopen an unfinished upload, so it asks for the file
  again.
- **Safe before 0034 is applied.** An upload matches and applies as before, and no product is
  Needs review.

Checked on 11 October 2026:
- The smoke test covers a product given Needs review beside one given Cost needed.
- On a copy of the local demo database, with the file store replaced by a dictionary, 15 of
  15 passed. Before 0034 the match worked and no product was Needs review. After 0034:
  - the match recorded one variant, and the brush became Needs review on both screens while
    the desk, whose cost matched, stayed Complete;
  - matching again kept one row;
  - applying without replacing cleared it, and the cost stayed 3.24;
  - a second upload brought it back, a newer unmatched upload settled it, and a cost set by
    hand settled it;
  - `mse_app` saw no row outside its account.
- In a browser at 390 and 1280 pixels wide, Products showed the chip and the product page
  showed the explanation, with no page scrolling sideways.

**0034 was applied on 11 October 2026**, with the owner's authority, to development, staging and production, each in one transaction with its record and checksum. Queried afterwards on all three, the table belongs to `mse_migrator` with row level security forced, and `mse_app` may insert and delete.

## A36.14 Item 6 built: Unmatched payouts, 11 October 2026

The owner ruled on 10 October 2026 that Unmatched is a payout with no statement behind it
(A36.2 answer 2). MyShopEdge read payouts only inside statements, so it never held one without a
statement. On 11 October 2026 the owner amended A11.5, so that TikTok's Get Payments may be read
for that one purpose, and pasted the response example from TikTok's page. Bank reconciliation
stays out of scope.

- Migration 0035 adds `tiktok_payments`: TikTok's payout id, status, amount, settlement and
  reserve amounts, currency, and when it was created and paid. Row level security follows the
  shop's account. The masked bank account TikTok returns is not stored.
- The daily sync reads the payouts at the end of the finance read, over the same window as the
  statements, and keeps each once. A refusal from TikTok, or a missing table before 0035, is
  noted on the run and never fails the finance read.
- A payout is Unmatched when no statement of the shop carries its id as `payment_id`.
  `listSettlements` serves them on its first page as `unmatched`, newest first, at most 100.
- The Payouts page shows them above the list, under Unmatched, with their reference, date and
  amount. They open nothing, because there is no statement to explain them.

**Unverified:**
- That the amounts are in pounds rather than pence. The example's "100" could be either. They
  are read in major units, as the statements' amounts are. The first real payout compared with
  its own statement settles it.
- How TikTok fills `status` beyond the example's PAID. It is shown as TikTok gives it.

Checked on 11 October 2026:
- The smoke test covers one Unmatched payout on the first page and none on a later page.
- `testdata/tiktok_sync_check.py` passed 50 of 50 on both datasets, five more checks than
  before. Its fake TikTok answers Get Payments in the pasted example's shape, with one payout
  per paid statement and one no statement names. Each payout was kept once across two runs,
  only the extra one was Unmatched, each matched payout read as its own statement's amount,
  and no bank account column exists.
- Without 0035 the finance read completed, with the note "payments not kept: migration 0035 is
  not applied".
- On a synced local database the Payouts list served the one Unmatched payout, £12.34, and an
  empty list once the table was removed. `mse_app` saw the shop's 3 payouts as the shop's
  account, and none as another account or with none.
- In a browser at 390 and 1280 pixels wide, the Payouts page showed the Unmatched card with no
  page scrolling sideways.

**0035 was applied on 11 October 2026**, with the owner's authority, to development, staging and production, each in one transaction with its record and checksum. Queried afterwards on all three, the table belongs to `mse_migrator` with row level security forced, `mse_app` may insert and update, and no bank account column exists. No payout has been read from TikTok yet: the first daily sync after the service redeploys is the first real call to Get Payments.
