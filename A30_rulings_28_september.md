# Action 30. Four rulings, 28 September 2026

The owner ruled on four open questions on 28 September 2026. Each was blocking code, and
each is recorded here so that the code can cite a document rather than a conversation.

## 30.1 Deleting an account

**Ruling.** A deletion closes the account at once and anonymises it after a grace period of
thirty days.

- **At the request.** Sign-in stops working for the account at once. Every connected shop is
  disconnected, and its TikTok tokens are marked revoked. The account is marked for
  deletion with the date the grace period ends.
- **During the thirty days.** The seller can cancel the deletion, and nothing has yet been
  erased.
- **When the thirty days end.** The account's name and email are erased, the stored TikTok
  tokens are erased, and every file under the account's prefixes in the file store is
  deleted (A10.8 as amended). The ledger rows stay, attached to no person, for the
  retention period, because the ledger is append-only and financial records carry a
  retention duty. They are deleted when that period ends.
- **What the seller is told.** Exactly the above. Emergent AI's version told the seller the
  deletion "includes" their orders, ledger and costs while erasing nothing, and that is the
  mistake this ruling exists to prevent.

**Open.** The length of the retention period for the anonymised ledger is not ruled here.
A10 records six years for the TikTok fee invoices. Whether the same period applies to the
ledger needs the Data Protection document, and until it is ruled the anonymised rows are
kept and nothing deletes them.

**Built, 28 September 2026.** `deleteMe`, `cancelAccountDeletion` and
`service/scripts/erase_accounts.py`, with migration 0025, S30 and the closing page. Three
parts of the ruling needed a reading, recorded here so they can be corrected.

- "Sign-in stops working" is read as: every operation refuses the account except getMe and
  the cancellation, because a seller who could not sign in at all could never cancel.
- The contract had no way to cancel, so `POST /me/deletion/cancel` was added to it.
- A cancelled deletion leaves the shops disconnected, because their tokens were revoked.

Three things the ruling does not cover are not built: what happens to a paid Stripe plan,
the confirmation email of A3's step 4, and a schedule that runs the erasure.

**Ruling, 7 October 2026. A deletion stops the plan renewing.** When a seller asks for
deletion, their Stripe subscription is set to end with the period already under way, or
with the free trial, so nothing more is charged and nothing is refunded. If the seller
cancels the deletion within the thirty days, renewal is turned back on. A seller who had
already stopped renewal before deleting keeps that choice.

**Built, 7 October 2026.** `billing.set_renewal_for_deletion` sets `cancel_at_period_end`
and marks the subscription's metadata with `renewal_stopped_by_deletion`, and the
cancellation clears both only where that mark is present. The Stripe call is made before the
account is closed, and a failure refuses the deletion with 502, so a seller is never left
closed and still being charged. S30 and the answer's `includes` say the plan stops renewing.
It has run against a stand-in Stripe client only (`test_handlers_smoke.py`), not against the
live account, because no test charge can be made there.

## 30.2 Checking a returned item

**Ruling.** The owner accepted all four proposals. `checkReturnItem` writes to the ledger
by these rules:

1. A write-off or return postage attaches to the order line of the variant that was
   returned, not to the order's first line.
2. A write-off uses the cost in force when the unit sold.
3. The entries carry the date of the check.
4. A check takes the checked units off `coming_back`.

## 30.3 The tax set-aside estimate

**Ruling.** The set-aside shows a simple estimate for a sole trader: income tax and Class 4
National Insurance on profit to date, at the bands in force, read from reference rules and
labelled as an estimate. A limited company sees no figure.

**Unverified.** The bands and rates must come from gov.uk. This session could not reach
gov.uk on 28 September, because the environment's network policy blocks it, so no band is
loaded until someone checks it against its source.

**Built, 28 September 2026.** `getTaxSetAside` applies the ruling in `service/app/tax.py`.
Profit to date is the Money screen's gross profit after returns, by sale date, from 6 April
to today, for the shop. The personal allowance with an optional taper, the income tax bands
and Class 4 are three reference rules whose shape the module documents. A rule counts only
once its `reviewed_at` is set. `tests/test_set_aside.py` checks the method on made-up round
numbers. No real band is loaded: production's `reference_rules` held 0 rows when queried
the same day, and gov.uk remained unreachable from the session.

## 30.4 Single-factor sign-in

**Ruling.** Sign-in without a second factor is accepted for launch. Neon Auth offers no
second factor and none can be added (A14.7). The risk is accepted knowingly: an account is
protected by the seller's own sign-in with Google, GitHub or Microsoft, which the provider
page offers, and by nothing further of ours.
