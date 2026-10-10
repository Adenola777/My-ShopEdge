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

## A36.4 Still to build, each step with the owner's approval

2. The journey: no extra click after TikTok, the brief's trial active page, the abandoned card
   step ("No changes were made…"), the first reconciliation screen, the cost choice and the
   gross profit reveal.
3. The definitions: the net sales order, gross profit so far, and cost coverage on every
   screen that shows profit.
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
