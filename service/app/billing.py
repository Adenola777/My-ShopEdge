"""Billing. The plans, the trial, and the Stripe webhook.

The trial is a Stripe Subscription created with a trial period and an incomplete payment
behaviour. Stripe returns a pending SetupIntent, the browser confirms it, and that
confirmation is where Strong Customer Authentication happens. Nothing is charged today.

Why a SetupIntent rather than a PaymentIntent or a small authorisation hold. Under the UK
SCA rules the card is authenticated at the moment it is saved, and the mandate recorded at
that moment is what allows the charge on day fifteen to be taken off session. A trial that
saves a card without authenticating it produces a first charge with no prior
authentication, and a meaningful share of UK issuers decline those.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Annotated, Literal

import stripe
from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel

from . import db
from .auth import Account, require_account
from .money import Money, money
from .plans import CYCLES, DEFAULT_CYCLE, PAID, PLAN_ORDER, PLANS, TRIAL_DAYS
from .problems import Problem

logger = logging.getLogger("myshopedge.billing")

router = APIRouter(tags=["Billing"])

# The database wiring below (the subscription row, GET /billing/subscription, and the
# webhook handlers) was written by Emergent AI in `Adenola777/MYSHOPEDGE` (commit 06faeba,
# 25 September 2026) and brought into this repository on 28 September at the owner's
# instruction. See audit/EMERGENT_review_28_september.md.
#
# The gap that review left, a second trial request creating a second subscription at Stripe,
# was closed on 29 September in `start_trial`: an account whose subscription is live is
# refused, and one whose trial was started but never confirmed is handed the same
# subscription again. A cancelled account may start again. Whether that second start
# should carry a second free trial is not ruled, so it does, as it did before.

LIVE = ("trialing", "active", "past_due")


def _stripe() -> stripe.StripeClient:
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        raise Problem(503, "billing_unconfigured",
                      "Plans cannot be started or changed just now. You have not been charged. Try again later.")
    return stripe.StripeClient(key)


Cycle = Literal["annual", "annual_monthly", "monthly"]
PaidPlan = Literal["starter", "growth", "pro"]


class CyclePriceOut(BaseModel):
    """One billing cycle's price. `charge` is one payment, `per_month` the monthly figure a
    card shows, `payments` the payments a term holds. `available` is False while the cycle's
    Stripe price identifier is unset, which is every cycle until the owner approves the
    prices (A38.3), so the cart can say checkout is not open and charge nothing."""
    cycle: Cycle
    charge: Money
    per_month: Money
    payments: int
    interval: Literal["year", "month"]
    available: bool


class PlanOut(BaseModel):
    slug: Literal["explorer", "starter", "growth", "pro"]
    name: str
    audience: str
    shop_limit: int
    order_limit: int | None
    history_days: int | None
    features: list[str]
    coming_soon: list[str]
    highlight: bool
    free: bool
    prices: list[CyclePriceOut]


class PlansOut(BaseModel):
    trial_days: int
    default_cycle: Cycle
    plans: list[PlanOut]


class TrialRequest(BaseModel):
    plan: PaidPlan
    cycle: Cycle = DEFAULT_CYCLE


def _price_id(slug: str, cycle: str) -> str | None:
    """The Stripe price identifier for a plan's cycle, from the environment only."""
    price = PLANS[slug].prices.get(cycle)
    return os.environ.get(price.env_var) if price else None


class TrialStart(BaseModel):
    status: Literal["requires_card", "trialing"]
    subscription_id: str
    trial_ends_at: str | None = None
    client_secret: str | None = None


class SubscriptionOut(BaseModel):
    """The account's billing state, mirrored from Stripe by the webhook.

    The status enum is the contract's, which has no 'incomplete'. A row that Stripe has
    not yet confirmed reads as 'none', because from the seller's side a trial that has not
    started has not started. `card_last4` is served as null: the service holds a reference
    to the card at Stripe and never a detail of it.
    """

    status: Literal["none", "trialing", "active", "past_due", "canceled"]
    plan: PaidPlan | None = None
    # The plan whose limits and features apply now (A38): the paid plan while it runs, and
    # Explorer for an account with none. `cycle` is worked out from the billing period's
    # length, so Annual, billed monthly reads as monthly until its price exists (A38.5).
    effective_plan: Literal["explorer", "starter", "growth", "pro"] = "explorer"
    cycle: Cycle | None = None
    shop_limit: int = 1
    trial_ends_at: str | None = None
    current_period_end: str | None = None
    card_last4: str | None = None
    # True when renewal is stopped, whether at the end of the period or, for Annual, billed
    # monthly, at the end of its twelve-payment term (A38.6). `ends_at` is the day the plan
    # then ends.
    cancel_at_period_end: bool = False
    ends_at: str | None = None
    # The end of the running twelve-payment term, on Annual, billed monthly only (A38.6).
    commitment_ends_at: str | None = None
    # What the plan unlocks, from `entitlements.py`. The browser shows or prompts from this
    # list, and every route checks the plan again itself, so the list grants nothing.
    features: list[str] = []


@router.get("/billing/plans", response_model=PlansOut, summary="The plans on sale")
def list_plans() -> PlansOut:
    """The price is served rather than held in the client, so a price change does not
    require a client release. A plan's `features` list only what the product does today;
    `coming_soon` lists what the owner placed in the plan that is not built (A38.3)."""
    return PlansOut(
        trial_days=TRIAL_DAYS,
        default_cycle=DEFAULT_CYCLE,
        plans=[
            PlanOut(
                slug=p.slug, name=p.name, audience=p.audience, shop_limit=p.shop_limit,
                order_limit=p.order_limit, history_days=p.history_days, features=p.features,
                coming_soon=p.coming_soon, highlight=p.highlight, free=p.free,
                prices=[
                    CyclePriceOut(
                        cycle=c, charge=money(pr.charge_minor, "GBP"),
                        per_month=money(pr.per_month_minor, "GBP"), payments=pr.payments,
                        interval=pr.interval, available=bool(os.environ.get(pr.env_var)),
                    )
                    for c, pr in ((c, p.prices[c]) for c in CYCLES if c in p.prices)
                ],
            )
            for p in (PLANS[s] for s in PLAN_ORDER)
        ],
    )


@router.post("/billing/subscription", response_model=TrialStart, summary="Start the free trial")
def start_trial(
    body: TrialRequest,
    account: Annotated[Account, Depends(require_account)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> TrialStart:
    plan = PLANS[body.plan]

    # The price identifier comes from the environment. A price sent by a client is never
    # trusted, because a seller could otherwise start a Pro trial at the Starter price. Until
    # the owner approves the A38 prices none is set, so this answers 503 (A38.3).
    price_id = _price_id(plan.slug, body.cycle)
    if not price_id:
        raise Problem(503, "plan_unavailable",
                      "This plan cannot be started at the moment. You have not been charged. "
                      "Choose another plan, or try again later.")

    existing = db.get_subscription_row(account.id)
    if existing is not None and existing["status"] in LIVE:
        raise Problem(409, "subscription_exists",
                      "This account already has a subscription, so nothing new was started.")

    client = _stripe()
    key = f"sub:{account.id}:{plan.slug}:{idempotency_key}" if idempotency_key else None

    # Named so a Stripe failure can be logged against the call that failed.
    step = "open_subscription"
    try:
        # A trial started earlier and never confirmed is still open at Stripe. Handing it
        # back lets the seller finish confirming the card without a second subscription.
        if existing is not None and existing["status"] == "incomplete" and existing["stripe_customer_id"]:
            open_sub = _open_subscription(client, existing["stripe_customer_id"])
            if open_sub is not None:
                return _trial_start(open_sub)

        step = "find_or_create_customer"
        customer = _find_or_create_customer(client, account, key, existing)
        step = "create_subscription"
        # The row is written before the Stripe subscription exists, so a webhook that
        # arrives the instant the subscription is created finds a customer to attach to.
        # It carries status 'incomplete' until an event confirms the trial has started.
        db.create_subscription_row(account.id, plan.slug, customer.id)
        subscription = client.subscriptions.create(
            params={
                "customer": customer.id,
                "items": [{"price": price_id}],
                "trial_period_days": TRIAL_DAYS,
                "payment_behavior": "default_incomplete",
                "collection_method": "charge_automatically",
                "payment_settings": {
                    "save_default_payment_method": "on_subscription",
                    "payment_method_types": ["card"],
                },
                # A trial that reaches its end with no payment method is cancelled rather
                # than left owing. The seller keeps their data and is asked for a card.
                "trial_settings": {"end_behavior": {"missing_payment_method": "cancel"}},
                "expand": ["pending_setup_intent"],
                "metadata": {"account_id": account.id, "plan": plan.slug, "cycle": body.cycle},
            },
            options={"idempotency_key": key} if key else None,
        )
    except stripe.CardError as exc:
        _log_stripe_error(account.id, step, exc)
        declined = (exc.user_message or "Your bank declined the card.").rstrip(". ") + "."
        raise Problem(402, "card_declined",
                      f"{declined} Nothing was charged and the trial has not started. "
                      "Try another card, or ask your bank why it declined.") from exc
    except stripe.StripeError as exc:
        _log_stripe_error(account.id, step, exc)
        raise Problem(502, "stripe_error",
                      "Our payment provider did not complete the request, so the trial has not "
                      "started and nothing was charged. Try again in a few minutes.") from exc

    # The subscription Stripe just returned already carries its status and trial end, so
    # the row is moved off 'incomplete' now rather than waiting for the webhook. The webhook
    # remains the authority and repeats this write when it arrives; the write is idempotent.
    _apply_stripe_subscription(subscription)
    return _trial_start(subscription)


def _log_stripe_error(account_id, step: str, exc: stripe.StripeError) -> None:
    """Records why Stripe refused a call, which the seller's message deliberately does not say.

    Added on 8 October 2026: seven trial starts on 7 October answered 502 and left no trace
    of Stripe's reason. The fields are the ones stripe-python 16 sets on every StripeError.
    Stripe's message masks an API key to its last four characters, and no card detail
    reaches this call, so nothing logged here is a secret.
    """
    err = exc.error
    logger.error(
        "stripe refused %s for account %s: %s http=%s type=%s code=%s param=%s request=%s message=%s",
        step,
        account_id,
        type(exc).__name__,
        exc.http_status,
        getattr(err, "type", None),
        exc.code,
        getattr(err, "param", None),
        exc.request_id,
        exc.user_message,
    )


# Set on the Stripe subscription when a deletion stopped its renewal, so that cancelling the
# deletion turns renewal back on only where the deletion turned it off. A seller who had
# already chosen to stop renewing before deleting keeps that choice.
DELETION_FLAG = "renewal_stopped_by_deletion"


def set_renewal_for_deletion(account_id, closing: bool) -> str:
    """Stops or restores renewal of the account's subscription, under the owner's ruling of
    7 October 2026: a deletion stops renewal at the end of the paid period, and cancelling
    the deletion turns renewal back on.

    Returns what was done: 'none' when the account has no live subscription at Stripe,
    'stopped', 'restored' or 'unchanged'. Raises Problem when Stripe cannot be reached, so the
    caller can refuse the deletion rather than leave a seller being charged.

    Setting `cancel_at_period_end` during a trial ends the subscription when the trial ends,
    so no charge is taken; that is Stripe's documented behaviour and has not been run against
    the live account. **Unverified against Stripe** for the reason `_open_subscription` gives.
    """
    row = db.get_subscription_row(account_id)
    if row is None or row["status"] not in LIVE or not row.get("stripe_subscription_id"):
        return "none"
    # The demo shop's trial is written straight into the database with a customer id that
    # Stripe never issued (testdata/load_demo.py), so there is nothing at Stripe to change.
    if str(row.get("stripe_customer_id") or "").startswith("demo_"):
        return "none"

    client = _stripe()
    try:
        sub = _plain(client.subscriptions.retrieve(row["stripe_subscription_id"]))
        flagged = (sub.get("metadata") or {}).get(DELETION_FLAG) == "true"
        stopped = bool(sub.get("cancel_at_period_end") or sub.get("cancel_at"))
        if closing and not stopped:
            # On Annual, billed monthly the plan ends when its twelve payments are done (A38.6).
            params = {**_renewal_params(row, stop=True), "metadata": {DELETION_FLAG: "true"}}
            outcome = "stopped"
        elif not closing and flagged:
            # Stripe removes a metadata key that is set to an empty string.
            params = {**_renewal_params(dict(row, cancel_at=sub.get("cancel_at")), stop=False),
                      "metadata": {DELETION_FLAG: ""}}
            outcome = "restored"
        else:
            return "unchanged"
        sub = client.subscriptions.update(row["stripe_subscription_id"], params=params)
    except stripe.StripeError as exc:
        raise Problem(502, "stripe_error",
                      "We could not reach our payment provider, so nothing was changed. "
                      "Try again in a few minutes.") from exc

    _apply_stripe_subscription(sub)
    logger.info("account %s renewal %s for deletion", account_id, outcome)
    return outcome


def _open_subscription(client: stripe.StripeClient, customer_id: str):
    """The customer's subscription that is still open at Stripe, or None.

    Open means waiting for a card or already running. The row can read 'incomplete' while
    Stripe has moved the subscription on, because the webhook is a moment behind, so a
    running subscription found here is written through and handed back rather than a second
    one being made. **Unverified against Stripe**, because only the live account is reachable
    and no test charge can be made (CLAUDE.md); it has run against a stand-in client only.
    """
    subs = client.subscriptions.list(
        params={"customer": customer_id, "status": "all", "limit": 10,
                "expand": ["data.pending_setup_intent"]},
    )
    for sub in subs.data:
        if sub.status in ("incomplete", *LIVE):
            _apply_stripe_subscription(sub)
            return sub
    return None


def _trial_start(subscription) -> TrialStart:
    intent = subscription.pending_setup_intent
    trial_ends = _iso(subscription.trial_end)

    # Stripe returns no setup intent when the customer already has a usable card on file.
    # That is a valid outcome and the trial has started.
    if intent is None or isinstance(intent, str) or not intent.client_secret:
        return TrialStart(status="trialing", subscription_id=subscription.id, trial_ends_at=trial_ends)

    return TrialStart(
        status="requires_card",
        subscription_id=subscription.id,
        trial_ends_at=trial_ends,
        client_secret=intent.client_secret,
    )


@router.get("/billing/subscription", response_model=SubscriptionOut, summary="The account's subscription")
def get_subscription(account: Annotated[Account, Depends(require_account)]) -> SubscriptionOut:
    """The seller's billing state, read from the row the webhook keeps.

    A seller who has never started a trial has no row, which reads as 'none'. A row still
    marked 'incomplete' is one Stripe has not confirmed to us yet, usually because the
    webhook is a moment behind. Rather than show the seller a stale 'none' just after they
    confirmed their card, the current state is fetched from Stripe once and written through
    the same path the webhook uses, so whichever arrives first wins.
    """
    row = db.get_subscription_row(account.id)
    if row is None:
        # No plan is Explorer, the free plan (A38).
        from .entitlements import BY_PLAN
        return SubscriptionOut(status="none", features=sorted(BY_PLAN["explorer"]),
                               effective_plan="explorer", shop_limit=PLANS["explorer"].shop_limit)

    if row["status"] == "incomplete":
        refreshed = _refresh_from_stripe(account.id, row.get("stripe_customer_id"))
        if refreshed is not None:
            row = refreshed

    return _subscription_out(row)


def _cycle_of(row: dict) -> str | None:
    """The plan's billing cycle. Since A38.6 it is the one the row holds, worked out from the
    price the plan is on. A row without one, written before migration 0036, falls back to the
    length of the billing period: a period longer than about forty days is a year, and Annual,
    billed monthly then reads as monthly."""
    if row.get("cycle") in CYCLES:
        return row["cycle"]
    start, end = row.get("current_period_start"), row.get("current_period_end")
    if not start or not end or row.get("status") == "trialing":
        return None
    return "annual" if (end - start).days > 40 else "monthly"


def _subscription_out(row: dict) -> SubscriptionOut:
    from .entitlements import features_for_row, plan_for_row  # entitlements imports LIVE from here

    status = row["status"]
    effective = plan_for_row(row)
    return SubscriptionOut(
        effective_plan=effective,
        cycle=_cycle_of(row),
        shop_limit=PLANS[effective].shop_limit,
        features=sorted(features_for_row(row)),
        status="none" if status == "incomplete" else status,
        plan=row["plan_slug"],
        trial_ends_at=_iso_dt(row["trial_end"]),
        current_period_end=_iso_dt(row["current_period_end"]),
        card_last4=None,
        cancel_at_period_end=bool(row["cancel_at_period_end"] or row.get("cancel_at")),
        ends_at=_iso_dt(row.get("cancel_at")
                        or (row["trial_end"] if status == "trialing" else row["current_period_end"])),
        commitment_ends_at=_iso_dt(row.get("commitment_ends_at")),
    )


# --- stopping renewal and changing the card (8 October 2026) ----------------------------------
#
# The billing screens told sellers they could cancel and change the card "in Settings", and
# Settings had neither. The owner chose on 8 October to build both in the app rather than use
# Stripe's hosted portal. **Unverified against Stripe**: only the live account is reachable,
# so these have run against stand-in clients in the smoke test only.


class RenewalRequest(BaseModel):
    """Either or both. A request carrying neither changes nothing and is refused."""
    cancel_at_period_end: bool | None = None
    plan: PaidPlan | None = None
    cycle: Cycle = DEFAULT_CYCLE


class CardSetupOut(BaseModel):
    client_secret: str


class CardSetRequest(BaseModel):
    setup_intent_id: str


def _live_row(account_id) -> dict:
    """The account's live subscription row, or a 409 that says nothing was changed."""
    row = db.get_subscription_row(account_id)
    if row is None or row["status"] not in LIVE or not row.get("stripe_subscription_id"):
        raise Problem(409, "no_live_subscription",
                      "This account has no plan running, so nothing was changed.")
    # The demo shop's plan was written straight into the database (testdata/load_demo.py);
    # Stripe has never heard of it.
    if str(row.get("stripe_customer_id") or "").startswith("demo_"):
        raise Problem(409, "demo_subscription",
                      "This is the demo shop's sample plan, so it cannot be changed.")
    return row


@router.patch("/billing/subscription", response_model=SubscriptionOut,
              summary="Stop the plan renewing, or turn renewal back on")
def update_subscription(
    body: RenewalRequest,
    account: Annotated[Account, Depends(require_account)],
) -> SubscriptionOut:
    if body.cancel_at_period_end is None and body.plan is None:
        raise Problem(422, "validation_failed", "Choose a plan, or whether the plan renews.")
    row = _live_row(account.id)
    params: dict = {}
    if body.cancel_at_period_end is not None:
        params.update(_renewal_params(row, stop=body.cancel_at_period_end))
        if not body.cancel_at_period_end:
            # A seller turning renewal back on owns the choice from now, so a flag a deletion
            # left is cleared. Stripe removes a metadata key that is set to an empty string.
            params["metadata"] = {DELETION_FLAG: ""}
    client = _stripe()
    # A cycle is compared only when it is known: during a trial the period does not say it.
    current_cycle = _cycle_of(row)
    if body.plan is not None and (body.plan != row["plan_slug"]
                                  or (current_cycle is not None and body.cycle != current_cycle)):
        change = _plan_change(client, account.id, row, body.plan, body.cycle)
        params["metadata"] = {**params.get("metadata", {}), **change.pop("metadata")}
        params.update(change)
    if not params:
        return _subscription_out(row)
    try:
        sub = client.subscriptions.update(row["stripe_subscription_id"], params=params)
    except stripe.StripeError as exc:
        _log_stripe_error(account.id, "update_subscription", exc)
        raise Problem(502, "stripe_error",
                      "We could not reach our payment provider, so nothing was changed. "
                      "Try again in a few minutes.") from exc
    _apply_stripe_subscription(sub)
    return _subscription_out(db.get_subscription_row(account.id))


def _plan_change(client: stripe.StripeClient, account_id, row: dict, slug: str,
                 cycle: str = DEFAULT_CYCLE) -> dict:
    """The Stripe parameters that move a running subscription to another plan.

    Added 10 October 2026 with the pricing tiers, because a seller shown an upgrade prompt had
    no way to act on it. The price comes from the environment, as in `start_trial`, never from
    the request. The subscription's one item has its price replaced, and `metadata.plan` is
    rewritten so that it never disagrees with the price. Stripe's default proration applies:
    on a paid period the difference for the days left is added to the next invoice, and during
    a trial nothing is charged. That is Stripe's documented default, not something this
    project has observed. **Unverified against Stripe**: only the live account is reachable,
    so this has run against the stand-in client in the smoke test only.
    """
    term_end = _running_commitment(row)
    if term_end is not None:
        # A38.6: during a twelve-payment term a seller may move up, or pay the rest of the year
        # at once on Annual prepaid, but not to Monthly or a smaller plan, which would cut what
        # the term owes. The change can be made once the term has ended.
        smaller = PLAN_ORDER.index(slug) < PLAN_ORDER.index(row["plan_slug"])
        if cycle == "monthly" or (cycle == "annual_monthly" and smaller):
            raise Problem(409, "commitment_running",
                          "Your plan is on Annual, billed monthly, and its twelve payments run until "
                          f"{term_end:%-d %B %Y}. You can move to a larger plan or to Annual prepaid "
                          "now, and to Monthly or a smaller plan after that date. Nothing was changed.")
    price_id = _price_id(slug, cycle)
    if not price_id:
        raise Problem(503, "plan_unavailable",
                      "Checkout is not open yet, so your plan was not changed and nothing was charged.")
    try:
        current = _plain(client.subscriptions.retrieve(row["stripe_subscription_id"]))
    except stripe.StripeError as exc:
        _log_stripe_error(account_id, "retrieve_for_plan_change", exc)
        raise Problem(502, "stripe_error",
                      "We could not reach our payment provider, so your plan was not changed. "
                      "Try again in a few minutes.") from exc
    item = _first_item(current)
    if item is None or not item.get("id"):
        raise Problem(409, "no_live_subscription",
                      "This account has no plan running, so nothing was changed.")
    metadata = {"plan": slug, "cycle": cycle}
    if cycle == "annual_monthly" and _cycle_of(row) != "annual_monthly":
        # A move onto Annual, billed monthly starts a twelve-payment term today, or when the
        # trial ends if the plan is still in its trial (A38.6).
        trial_end = current.get("trial_end") if current.get("status") == "trialing" else None
        metadata["term_start"] = str(int(trial_end or datetime.now(timezone.utc).timestamp()))
    elif cycle != "annual_monthly" and _cycle_of(row) == "annual_monthly":
        metadata["term_start"] = ""  # Stripe removes a key set to an empty string
    return {"items": [{"id": item["id"], "price": price_id}], "metadata": metadata}


@router.post("/billing/card", response_model=CardSetupOut,
             summary="Start replacing the card the plan charges")
def start_card_change(account: Annotated[Account, Depends(require_account)]) -> CardSetupOut:
    row = _live_row(account.id)
    try:
        intent = _stripe().setup_intents.create(params={
            "customer": row["stripe_customer_id"],
            "usage": "off_session",
            "metadata": {"account_id": str(account.id), "purpose": "card_change"},
        })
    except stripe.StripeError as exc:
        _log_stripe_error(account.id, "start_card_change", exc)
        raise Problem(502, "stripe_error",
                      "We could not reach our payment provider, so your card was not changed. "
                      "Try again in a few minutes.") from exc
    return CardSetupOut(client_secret=intent.client_secret)


@router.put("/billing/card", response_model=SubscriptionOut,
            summary="Make a confirmed card the one the plan charges")
def set_card(
    body: CardSetRequest,
    account: Annotated[Account, Depends(require_account)],
) -> SubscriptionOut:
    row = _live_row(account.id)
    client = _stripe()
    try:
        intent = _plain(client.setup_intents.retrieve(body.setup_intent_id))
        # The intent must be this account's own, and the bank must have finished with it.
        # Another customer's intent is refused with the same words as an unfinished one, so
        # the answer says nothing about intents that are not this seller's.
        method = intent.get("payment_method")
        if isinstance(method, dict):
            method = method.get("id")
        if (intent.get("customer") != row["stripe_customer_id"]
                or intent.get("status") != "succeeded" or not method):
            raise Problem(409, "card_not_confirmed",
                          "That card was not confirmed, so the card on your plan is unchanged. "
                          "Please try again.")
        client.customers.update(row["stripe_customer_id"], params={
            "invoice_settings": {"default_payment_method": method}})
        sub = client.subscriptions.update(row["stripe_subscription_id"], params={
            "default_payment_method": method})
    except stripe.StripeError as exc:
        _log_stripe_error(account.id, "set_card", exc)
        raise Problem(502, "stripe_error",
                      "We could not reach our payment provider, so your card was not changed. "
                      "Try again in a few minutes.") from exc
    _apply_stripe_subscription(sub)
    return _subscription_out(db.get_subscription_row(account.id))


@router.post("/webhooks/stripe", summary="Stripe events", include_in_schema=True)
async def stripe_webhook(request: Request, stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None):
    """Authenticated by the signature header rather than by a bearer token.

    Delivery is at least once and events can arrive out of order, so every handler is
    idempotent: each reads the subscription's current state from Stripe and writes that,
    rather than a delta or the event's own copy, so a repeated or late event lands the same
    value as the newest one.

    An event whose customer we hold no row for is logged and accepted with a 200. It is not
    ours to act on, it belongs to another environment's Stripe account, and answering
    anything other than 200 would have Stripe redeliver it for days.
    """
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret or not stripe_signature:
        raise Problem(400, "signature_missing", "The signature did not verify.")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, secret)
    except Exception as exc:  # signature or payload failure
        raise Problem(400, "signature_invalid", "The signature did not verify.") from exc

    etype = event["type"]
    obj = _plain(event["data"]["object"])
    logger.info("stripe webhook %s %s received", event.get("id"), etype)

    try:
        if etype in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            # The subscription is read back from Stripe rather than taken from the event, so a
            # late, older event writes Stripe's current state and cannot undo a newer one
            # (A36, the brief's "idempotent" webhook). A deleted subscription is still
            # returned by Stripe with status canceled. **Unverified against Stripe**: only the
            # live account is reachable, so this has run against the stand-in client only.
            current = _stripe().subscriptions.retrieve(obj["id"]) if obj.get("id") else obj
            _apply_stripe_subscription(current)
        elif etype == "invoice.payment_failed":
            # The invoice names its subscription. Reading it back gives the accurate status
            # Stripe has moved it to, rather than this handler guessing 'past_due'.
            sub_id = obj.get("subscription")
            if sub_id:
                _apply_stripe_subscription(_stripe().subscriptions.retrieve(sub_id))
            elif obj.get("customer"):
                db.apply_subscription_event(
                    obj["customer"], None, None, "past_due", None, None, None, None
                )
    except Exception as exc:  # noqa: BLE001
        if "unknown_stripe_customer" in str(exc):
            logger.warning(
                "stripe webhook %s for a customer with no subscription row; ignored",
                etype,
            )
        else:
            raise

    return {"received": True}


def _find_or_create_customer(client: stripe.StripeClient, account: Account, key: str | None,
                             existing: dict | None = None):
    # The customer recorded on the account's row is used when there is one. Stripe's search
    # is not read-after-write, "in under 1 minute" by its own page, so two quick requests
    # searching for a customer just created could each make one (audit H2).
    if existing is not None and existing.get("stripe_customer_id"):
        return client.customers.retrieve(existing["stripe_customer_id"])
    found = client.customers.search(params={"query": f"metadata['account_id']:'{account.id}'", "limit": 1})
    if found.data:
        return found.data[0]
    return client.customers.create(
        params={"email": account.email, "name": account.name, "metadata": {"account_id": account.id}},
        options={"idempotency_key": f"cus:{key}"} if key else None,
    )


# The mapping from a Stripe subscription to the row, in one place.
#
# The database enum is trialing, active, past_due, canceled, incomplete. Stripe carries
# more, so unpaid is read as past_due because the seller must act, and incomplete_expired
# and paused are read as canceled because the subscription is not going to bill again
# without a fresh start. The plan slug is taken from the price identifier, and the metadata
# this service set when it created the subscription is the fallback (10 October 2026; before
# then it was the other way round).
_STATUS_MAP = {
    "trialing": "trialing",
    "active": "active",
    "past_due": "past_due",
    "unpaid": "past_due",
    "canceled": "canceled",
    "incomplete": "incomplete",
    "incomplete_expired": "canceled",
    "paused": "canceled",
}


def _map_status(stripe_status: str | None) -> str:
    return _STATUS_MAP.get(stripe_status or "", "incomplete")


def _slug_for_subscription(sub) -> str | None:
    """The plan a Stripe subscription is on. The price identifier decides, as the pricing
    ruling of 10 October 2026 requires: any of a plan's three A38 cycle prices, or the price it
    was sold at before A38 (`legacy_env_var`). `metadata.plan` is read only when the price
    matches none, as when a variable is not set."""
    price_id = _first_price_id(sub)
    if price_id:
        for candidate in PAID:
            plan = PLANS[candidate]
            env_vars = [pr.env_var for pr in plan.prices.values()] + [plan.legacy_env_var]
            if any(v and os.environ.get(v) == price_id for v in env_vars):
                return candidate
    slug = (sub.get("metadata") or {}).get("plan")
    return slug if slug in PAID else None


def _first_item(sub):
    items = sub.get("items") or {}
    data = items.get("data") if hasattr(items, "get") else getattr(items, "data", None)
    return data[0] if data else None


def _first_price_id(sub) -> str | None:
    item = _first_item(sub)
    if item is None:
        return None
    price = item.get("price") if hasattr(item, "get") else None
    return price.get("id") if price else None


def _sub_periods(sub) -> tuple[datetime | None, datetime | None]:
    start = sub.get("current_period_start")
    end = sub.get("current_period_end")
    # Newer Stripe API versions carry the period on the item rather than the subscription.
    if start is None or end is None:
        item = _first_item(sub)
        if item is not None:
            start = start or item.get("current_period_start")
            end = end or item.get("current_period_end")
    return _dt(start), _dt(end)


def _plain(obj):
    """A Stripe object as a plain dict, so the readers below can use `.get`.

    Found 8 October 2026 by the first trial start to reach Stripe with a valid key: in
    stripe-python 16 a StripeObject is not a dict, and `sub.get("customer")` raised, so every
    trial start failed after Stripe had created the subscription. `to_dict()` converts nested
    objects too. Anything else, such as the stand-ins in the smoke test, is returned as is.
    """
    return obj.to_dict() if isinstance(obj, stripe.StripeObject) else obj


def _apply_stripe_subscription(sub) -> None:
    """Writes a Stripe subscription's current state through the one write path."""
    sub = _plain(sub)
    customer = sub.get("customer")
    if isinstance(customer, dict):
        customer = customer.get("id")
    if not customer:
        return
    start, end = _sub_periods(sub)
    db.apply_subscription_event(
        stripe_customer_id=customer,
        stripe_subscription_id=sub.get("id"),
        plan_slug=_slug_for_subscription(sub),
        status=_map_status(sub.get("status")),
        trial_end=_dt(sub.get("trial_end")),
        period_start=start,
        period_end=end,
        cancel_at_period_end=bool(sub.get("cancel_at_period_end")),
    )
    cycle = _cycle_for_subscription(sub)
    written = db.apply_subscription_terms(
        stripe_customer_id=customer,
        cycle=cycle,
        cancel_at=_dt(sub.get("cancel_at")),
        commitment_ends_at=_commitment_end(sub, cycle),
    )
    if not written:
        logger.warning("subscription terms not written: migration 0036 is not applied")


def _refresh_from_stripe(account_id, customer_id: str | None) -> dict | None:
    """Reads the customer's current subscription from Stripe and writes it through.

    Returns the freshly read row, or None when Stripe cannot be reached or the customer has
    no subscription. Failure is not fatal: the caller falls back to the row it already has.
    """
    if not customer_id:
        return None
    try:
        subs = _stripe().subscriptions.list(
            params={"customer": customer_id, "status": "all", "limit": 1}
        )
    except (stripe.StripeError, Problem):
        # Problem is billing_unconfigured, when no Stripe key is set. Found 10 October 2026 on
        # the local copy: it reached the seller as a 503 although this read is optional.
        return None
    if not subs.data:
        return None
    try:
        _apply_stripe_subscription(subs.data[0])
    except Exception as exc:  # noqa: BLE001
        if "unknown_stripe_customer" not in str(exc):
            raise
        return None
    return db.get_subscription_row(account_id)


# --- the twelve-payment term of Annual, billed monthly (A38.6, 11 October 2026) ----------------
#
# The owner asked on 11 October 2026 for the commitment to be built: a seller on Annual, billed
# monthly owes all twelve payments of a term, even after stopping renewal. The term starts when
# the trial ends, or on the day a running plan moves onto the cycle (`metadata.term_start`), and
# lasts twelve calendar months. Stopping renewal during a term asks Stripe to cancel the plan on
# the day the term ends (`cancel_at`), so the remaining monthly payments are still taken and no
# more after them. A plan whose renewal is left on starts a new term of twelve. Stopping during
# the free trial ends the plan when the trial ends, as on every cycle, because no payment has
# yet fallen due. **Unverified against Stripe**: only the live account is reachable, so this
# has run against stand-in clients only.


def _add_months(value: datetime, months: int) -> datetime:
    """The same day `months` calendar months on, or the month's last day when it is shorter."""
    import calendar
    index = value.month - 1 + months
    year, month = value.year + index // 12, index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _cycle_for_subscription(sub) -> str | None:
    """The cycle of the price a Stripe subscription is on. A price sold before A38 is monthly.
    `metadata.cycle`, which this service sets, is read only when no price variable matches."""
    price_id = _first_price_id(sub)
    if price_id:
        for slug in PAID:
            plan = PLANS[slug]
            for cycle, price in plan.prices.items():
                if os.environ.get(price.env_var) == price_id:
                    return cycle
            if plan.legacy_env_var and os.environ.get(plan.legacy_env_var) == price_id:
                return "monthly"
    cycle = (sub.get("metadata") or {}).get("cycle")
    return cycle if cycle in CYCLES else None


def _commitment_end(sub, cycle: str | None, now: datetime | None = None) -> datetime | None:
    """The end of the running twelve-payment term, or None on any other cycle."""
    if cycle != "annual_monthly" or sub.get("status") in ("canceled", "incomplete_expired"):
        return None
    start = str((sub.get("metadata") or {}).get("term_start") or "")
    begun = int(start) if start.isdigit() else (sub.get("trial_end") or sub.get("start_date"))
    if not begun:
        return None
    payments = PLANS[PAID[0]].prices["annual_monthly"].payments
    end = _add_months(_dt(begun), payments)
    now = now or datetime.now(timezone.utc)
    # A plan cancelled for a date keeps that term; one left to renew moves to its next term.
    while end <= now and not sub.get("cancel_at"):
        end = _add_months(end, payments)
    return end


def _running_commitment(row: dict, now: datetime | None = None) -> datetime | None:
    """The end of the term a seller is bound by now: on Annual, billed monthly, out of the trial,
    before the term's end. None otherwise."""
    end = row.get("commitment_ends_at")
    now = now or datetime.now(timezone.utc)
    if _cycle_of(row) != "annual_monthly" or row.get("status") == "trialing" or end is None or end <= now:
        return None
    return end


def _renewal_params(row: dict, stop: bool) -> dict:
    """The Stripe parameters that stop or restore renewal for the row's plan.

    Stopping during a twelve-payment term sets `cancel_at` to the term's end, with no
    proration, so the remaining payments are taken. Otherwise renewal stops at the end of the
    period. Restoring clears whichever was set. The two are never sent together, because
    whether Stripe accepts both at once has not been checked.
    """
    if stop:
        term_end = _running_commitment(row)
        if term_end is not None:
            return {"cancel_at": int(term_end.timestamp()), "proration_behavior": "none"}
        return {"cancel_at_period_end": True}
    if row.get("cancel_at"):
        return {"cancel_at": ""}
    return {"cancel_at_period_end": False}


def _dt(seconds: int | None) -> datetime | None:
    if seconds is None:
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def _iso_dt(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _iso(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
