# A35. The pricing tiers

Written 10 October 2026, when the owner sent "MyShopEdge Final Pricing Packaging and Code
Command" and said "build the pricing tiers now". The owner answered two questions the same day,
recorded in A35.1. The document itself is the owner's; this file records how it was built and
what is still unverified.

## A35.1 What the owner chose

1. **Three plans, at the prices already live in Stripe.** Starter £9.99 for up to 100 orders a
   month, Growth £24.99 for up to 500, Pro £49.99 for up to 2,000. Every plan connects one
   TikTok Shop and starts with a thirty day trial. No price in Stripe changed, and no product or
   price was created.
2. **An account with no live plan keeps everything.** The owner chose "Everything, as today".
   A plan limits only while its status is trialing, active or past_due. An account with no
   subscription, or one that is incomplete or cancelled, keeps every feature.
3. **Pro gets the review list and export history.** The owner chose "Build priority review,
   gate history". Pro lists the statements that need review first, and the list of recent
   export files is Pro's.
4. **The VAT line reads "VAT is not currently charged."** The document's own line, "Any
   applicable VAT is shown at checkout", is not used, because A15.6 as amended on 30 September
   says no VAT is charged.

## A35.2 What each plan holds

`service/app/entitlements.py` holds the mapping, and it is the only place it is held.

| Feature | Starter | Growth | Pro | What it covers |
|---|---|---|---|---|
| `costs` | no | yes | yes | Cost upload, cost entry, cost lists and coverage |
| `profit` | no | yes | yes | Cost of goods, gross profit, margin, stock written off |
| `drilldown` | no | yes | yes | Records, and one product's page |
| `exports` | no | yes | yes | Requesting an export and reading its status |
| `basis` | no | yes | yes | The cash basis on any reading screen |
| `scheduled_exports` | no | no | yes | The four schedule routes, and the daily runner |
| `export_history` | no | no | yes | The list of recent export files |
| `priority_review` | no | no | yes | `getPayoutReview` |

Starter keeps Overview, the net proceeds chain, payouts and statements, refunds and returns,
products ranked by net proceeds, stock and the VAT monitor. A seller's own copy of their data
(`/me/export`) is not a plan feature and is open on every plan.

## A35.3 How it is enforced

- **The plan is read from the database row the Stripe webhook writes**, never from a request.
  Since 10 October 2026 `billing._slug_for_subscription` reads the price identifier first and
  falls back to `metadata.plan` only when the price matches none of the three variables. Before
  that the metadata came first.
- **A refused route answers 403 `plan_upgrade_required`**, with the RFC 9457 extension members
  `required_plan` and `feature`. Each gated operation carries `x-plan-feature` in the contract.
- **Starter's reading screens carry no profit.** `money_view.calculate` takes `profit=False`:
  the chain stops at Net proceeds, the seller's postage and return postage keep their lines
  under section totals, stock written off is left out, and `kept_reason` is the new
  `not_on_plan`. The product ranking answers the default with `measure` net_proceeds, and every
  row's `kept_reason` is the document's sentence, "Add product costs with Growth to see gross
  profit and margin by product." Insights are worked out with no cost. Today's Needs you drops
  the missing costs item, because the seller cannot act on it.
- **The scheduled export runner skips an account that has left Pro**, and leaves the schedule in
  place.
- **`getSubscription` serves `features`**, so the screens can choose what to offer. The list
  grants nothing, because every route checks the plan itself.

## A35.4 Changing plan

`updateSubscription` takes `plan` since 10 October 2026. It replaces the price on the
subscription's one item and rewrites `metadata.plan`, with the price taken from the service's
environment. Stripe's default proration is left in place. The page `/billing/change` states the
current plan, the new price and what happens to billing, and changes nothing until the seller
presses the button.

**Unverified against Stripe.** Only the live account is reachable, so the change has run
against the stand-in client in the smoke test only. That Stripe charges nothing during a trial
and adds the difference to the next invoice on a paid period is Stripe's documented default,
not something this project has observed.

## A35.5 The prompts

Each prompt is a card in the page, never a modal, and states the plan's price from the
service, the seller's trial or plan status, the capability in the document's own words, a
Choose action and "Not now". The document gives no sentence for the orders behind a figure or
for export history, so those two were written in the same form (`web/src/lib/upgrade.js`).

The document asks that no prompt appears before the seller has seen net proceeds. Prompts
appear only on a gated page or action, never on Overview, Money or Products themselves, and the
costs step of setting up is skipped on Starter rather than prompted.

## A35.6 Open

- **The one live subscription is Starter.** Production held one subscription when queried on
  10 October 2026: `inspirecraftglobal@gmail.com`, Starter, trialing until 7 November 2026, with
  no costs and no schedules. Once this is deployed that account sees Starter's limits.
- **The set-aside on Tax is not gated.** It is tax guidance and reads gross profit internally.
  With no costs on Starter it reports incomplete costs, as it does today for any seller without
  costs. The document does not name it.
- **Order-limit copy.** The document's usage sentence is added to Today's card beside the
  larger plan; the card's earlier wording, approved under A16.3, stays.
- **Validation metrics** in the document (plan split, conversion by plan, prompt conversion)
  are not built. Nothing records a prompt being shown or chosen.
