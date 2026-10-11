# A38. Pricing and checkout, the four plans

Written 11 October 2026. That day the owner gave a full specification for "a Zoom-style
pricing and checkout experience": four plans, three billing cycles, a cart before payment,
locked features shown with the plan that unlocks them, and the copy for each state. This file
records the rulings the specification makes and the two answers he gave the same day. Where a
ruling below conflicts with an earlier one, this file wins for the point it names (A29.11).

## A38.1 The plans

| | Explorer | Starter | Growth | Pro |
|---|---|---|---|---|
| Price, monthly | Free, no credit card required | £19 | £39 | £79 |
| Annual prepaid | | £190 a year (£15.83 a month) | £390 (£32.50) | £790 (£65.83) |
| Annual, billed monthly | | £17.25 × 12 | £35.42 × 12 | £72.08 × 12 |
| Connected TikTok Shops | 1 | 1 | Up to 3 | Up to 10 |
| Monthly order limit | 100 | 500 | 1,000 | Unlimited |
| Data history | 30 days | 12 months | 24 months | Unlimited |

Annual prepaid is the default cycle, because it is the best value. Annual, billed monthly
carries the disclosure that all 12 payments are owed even after a cancellation. Every price
reads "Excludes VAT where applicable"; Inspirecraft Global Ltd is not VAT registered
(30 September 2026), so no VAT is charged today.

## A38.2 What each plan includes

The specification's feature list and comparison table are the source, and
`service/app/plans.py` holds them. The central message is the owner's: everyone can upload
costs, Starter helps you understand profit, Growth lets you export and manage several shops,
and Pro gives agencies, accountants and high-volume sellers unlimited scale.

The service enforces these, from the plan Stripe reports (`entitlements.py`):

| Feature | First plan | Where it is enforced |
|---|---|---|
| Product costs, uploaded or typed | Explorer | Every plan |
| Gross profit | Explorer | Every plan |
| Gross margin | Starter | Margin fields are withheld from Explorer's money and product reads |
| The orders behind a figure | Starter | `/records` and a product's transactions |
| The full payout explanation | Starter | `getSettlement` |
| Exports | Growth | Every export route |
| VAT threshold tracker | Growth | The VAT part of `/tax` |
| Cash basis | Growth | Unchanged from A35 |
| Scheduled exports, export history, the review list | Pro | Unchanged from A35 |
| Connected shops | Per plan | A new connection beyond the plan's limit is refused |

Return and write-off treatment is not withheld from Explorer. The service posts return costs
whatever the plan, because the ledger must balance, and the Overview and Products show
Explorer those lines as they show every plan. Only the comparison table and the Products lock
block name the treatment as a Starter feature. Withholding the lines would change Explorer's
gross profit, so it is left for the owner to rule on.

The landing page, `site/index.html`, carries no prices. On 11 October 2026 the owner ruled
that the app's pricing page is the one place for them, so the landing page's Pricing links
go there, and its calls to action start Explorer rather than a trial.

## A38.3 The owner's answers of 11 October 2026

1. **Checkout stays off until he approves the prices.** The new prices need nine new prices
   in the live Stripe account, which CLAUDE.md rule 3 forbids without his explicit
   instruction, and a Stripe price cannot be edited once created. The screens, the cart and
   the gating are built; each cycle's price identifier is read from its own environment
   variable (`STRIPE_PRICE_<PLAN>_<CYCLE>`), and while none is set the cart says checkout is
   not open yet and charges nothing. No Stripe object was created.
2. **Features not built are shown as "Coming soon".** Accountant and team seats, client
   workspaces, the multi-shop consolidated view, shop-by-shop comparison, reconciliation
   status history and priority support appear in the cards and the table with that label,
   so the plan's shape is visible and nothing is sold that does not exist.

## A38.4 What this replaces

- **A35's three plans and prices** (£9.99, £24.99, £49.99, with costs on Growth only).
- **A36's "no figures before a trial starts".** An account with no plan is now on Explorer
  and sees its figures within Explorer's limits.
- **History of twenty-four months on every plan** (A16.2). History now differs by plan.
- **The soft order limit** (A16.3) for the last step only: at 100 per cent the
  specification says new orders stop syncing until the billing period resets or the seller
  upgrades.

## A38.5 Open, and not built in this change

Recorded so that none of it is advertised or assumed.

- **The price identifiers.** Nine prices await the owner's approval of each amount.
- **The commitment behind Annual, billed monthly.** Stripe has no plain price that holds a
  seller to twelve payments; it needs a subscription schedule or a contract term. Not
  designed.
- **Whether a paid plan keeps the 30-day free trial.** The specification is silent. The
  trial code is unchanged, so a checkout would still start one when checkout opens.
- **Data history limits are not enforced.** A seller sees more history than the plan states
  until the reads are bounded.
- **The 100 per cent order stop is not enforced.** The screens say what the specification
  says; the daily sync still reads every order. Production held no account near a limit on
  11 October 2026 (the most was 20 orders this month against Explorer's 100).
- **"Bulk cost upload".** The comparison table marks it Starter, while rule 1 says every
  plan may upload a cost file. The difference between a cost upload and a bulk cost upload
  is not defined, so Explorer may upload a file and the row is shown as the table reads.
- **Existing subscriptions.** The one live subscription on production on 11 October 2026,
  a Starter trial on the old £9.99 price, keeps its price; its plan now carries the new
  Starter features. Its account holds two shops against Starter's one, so it is asked to
  disconnect one and nothing is blocked.
- **The billing cycle of a running plan** is worked out from the length of its billing
  period, so Annual prepaid and Monthly can be told apart; Annual, billed monthly cannot be
  told from Monthly until its price exists.

**Unverified**: everything here has run against the local copy and stand-ins only. No
checkout has run, because none can until the prices exist.
