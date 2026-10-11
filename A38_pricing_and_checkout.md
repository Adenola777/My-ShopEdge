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

## A38.6 The nine prices and the twelve-payment term, built 11 October 2026

On 11 October 2026 the owner approved the nine amounts of A38.1 exactly as they stand, asked for
all nine prices to be created, and asked for the commitment behind Annual, billed monthly to be
built. He asked whether another plan can be added later; it can, as a new product and new
prices, while a price already created cannot be changed. This replaces the first two points of
A38.5.

**The prices.** `service/scripts/setup_stripe.py` creates them, and the owner runs it in his own
terminal, because the live key never enters a session (CLAUDE.md rule 2). Without `--apply` it
only says what it would create. Each price is GBP, exclusive of tax as the prices of
23 September are, and carries the lookup key `myshopedge_<plan>_<cycle>_a38`. It finds the
three products by `metadata['plan']` and, with a live key, stops before creating anything if
one is missing, because the instruction covered prices and not products. It never archives a
price, so the one live subscription on the old Starter price keeps it. It prints the nine
`STRIPE_PRICE_<PLAN>_<CYCLE>` variables to set on `My-ShopEdge-1`; checkout opens for a cycle
when its variable is set. It has run against a stand-in client only: a dry run, a refused live
run without `I_MEAN_LIVE=yes`, a live run creating nine prices on the three existing products, a
second run creating nothing, a changed amount stopping the run, and a missing product stopping
it before any price was made.

**The term.** Annual, billed monthly is an ordinary monthly price at Stripe. The service keeps
the term (`billing.py`, from `_add_months` to `_renewal_params`):

- A term is twelve calendar months. It starts when the trial ends, or on the day a running plan
  moves onto the cycle (`metadata.term_start` on the Stripe subscription).
- Stopping renewal during a term asks Stripe to cancel on the term's last day (`cancel_at`,
  with no proration), so the payments left are still taken and none after them. The seller is
  told this before confirming, and Profile and plan then reads "Plan ends" on that day.
- During a term a move to Monthly or to a smaller plan is refused with 409
  `commitment_running`, naming the day it becomes possible. A larger plan and Annual prepaid are
  allowed.
- A deletion during a term stops renewal the same way, as A30.1 stops it at the end of a period.

Migration 0036 adds `cycle`, `cancel_at` and `commitment_ends_at` to `subscriptions`, written by
a new SECURITY DEFINER function, `apply_subscription_terms`, owned by `mse_migrator` and callable
by `mse_app` alone. The cycle now comes from the price, so Annual, billed monthly no longer
reads as Monthly. **0036 is applied to no Neon branch.** The service reads and writes without
the new columns when they are absent, so it can deploy before or after the migration; until
0036 is applied the term is enforced but not shown, because the end date has nowhere to live.

**Checked**: the handler smoke test with a new case covering the dates, the Stripe parameters,
the refusals and the fallback without 0036; the contract test; ruff; 0036 built from empty on a
local PostgreSQL 16 with 37 migrations recorded, and on a local copy owned as Neon's is, where
`mse_app` wrote the columns, a cycle outside the three and an unknown customer were refused,
and `mse_analytics` could not call the function; the service reading and writing against a
local database with 0036 and one without it; and Profile and plan, Pricing and the move to
Explorer read in a browser with a temporary plan on the local copy, which was then put back
exactly. **Unverified against Stripe**: whether `cancel_at` with no proration takes the payments
left and no more, because no test charge can be made (CLAUDE.md).

**Open, for the owner to rule.**

1. **A deletion during a term.** The ruling that all twelve payments are owed means payments
   continue after the account is erased on day thirty (A30.1), for up to eleven months, while
   the seller can no longer sign in. Built as ruled; it may need a different rule.
2. **After the twelfth payment.** A plan whose renewal is left on starts a new term of twelve.
   The specification does not say; this mirrors Annual prepaid renewing for a year.
3. **Stopping during the trial** ends the plan when the trial ends with nothing owed, on this
   cycle as on the others, because no payment has fallen due.
4. **Whether a paid plan keeps the thirty-day trial** is still open from A38.5.
