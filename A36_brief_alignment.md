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

## A36.6 Still to build, each step with the owner's approval
4. The navigation in A36.1 item 4.
5. Overview and Reconcile, with the six statuses and "Explain this payout".
6. Products, Returns, Stock, Exports, and VAT and tax, as the brief sets them out.
7. The cost upload: a template, a preview, and the five row statuses. Existing costs are shown
   before they are replaced, and dates in the file are used.
8. Settings, the app footer's legal and support links, and the colour changes. Each colour
   change goes to the owner first.

Deleting the data of a shop whose account never starts a trial, 30 days after connection, is
not built. It removes data, so it needs the owner's approval of the job before it runs, and the
Privacy Policy needs the same period.
