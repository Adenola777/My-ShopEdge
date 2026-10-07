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
from .plans import PLAN_ORDER, PLANS, TRIAL_DAYS
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
        raise Problem(503, "billing_unconfigured", "Billing is not configured.")
    return stripe.StripeClient(key)


class PlanOut(BaseModel):
    slug: str
    name: str
    strapline: str
    price: Money
    order_limit: int
    history_months: int
    features: list[str]
    highlight: bool


class PlansOut(BaseModel):
    trial_days: int
    plans: list[PlanOut]


class TrialRequest(BaseModel):
    plan: Literal["starter", "growth", "pro"]


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
    plan: Literal["starter", "growth", "pro"] | None = None
    trial_ends_at: str | None = None
    current_period_end: str | None = None
    card_last4: str | None = None
    cancel_at_period_end: bool = False


@router.get("/billing/plans", response_model=PlansOut, summary="The plans on sale")
def list_plans() -> PlansOut:
    """The price is served rather than held in the client, so a price change does not
    require a client release. A plan lists only what the product does today."""
    return PlansOut(
        trial_days=TRIAL_DAYS,
        plans=[
            PlanOut(
                slug=p.slug,
                name=p.name,
                strapline=p.strapline,
                price=money(p.price_minor, p.currency),
                order_limit=p.order_limit,
                history_months=p.history_months,
                features=p.features,
                highlight=p.highlight,
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
    # trusted, because a seller could otherwise start a Pro trial at the Starter price.
    price_id = os.environ.get(plan.price_env_var)
    if not price_id:
        raise Problem(503, "plan_unavailable", "This plan is not configured yet. Nobody has been charged.")

    existing = db.get_subscription_row(account.id)
    if existing is not None and existing["status"] in LIVE:
        raise Problem(409, "subscription_exists",
                      "This account already has a subscription, so nothing new was started.")

    client = _stripe()
    key = f"sub:{account.id}:{plan.slug}:{idempotency_key}" if idempotency_key else None

    try:
        # A trial started earlier and never confirmed is still open at Stripe. Handing it
        # back lets the seller finish confirming the card without a second subscription.
        if existing is not None and existing["status"] == "incomplete" and existing["stripe_customer_id"]:
            open_sub = _open_subscription(client, existing["stripe_customer_id"])
            if open_sub is not None:
                return _trial_start(open_sub)

        customer = _find_or_create_customer(client, account, key, existing)
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
                "metadata": {"account_id": account.id, "plan": plan.slug},
            },
            options={"idempotency_key": key} if key else None,
        )
    except stripe.CardError as exc:
        raise Problem(402, "card_declined", exc.user_message or "Your bank declined the card.") from exc
    except stripe.StripeError as exc:
        raise Problem(502, "stripe_error", "We could not start the trial. Nobody has been charged.") from exc

    # The subscription Stripe just returned already carries its status and trial end, so
    # the row is moved off 'incomplete' now rather than waiting for the webhook. The webhook
    # remains the authority and repeats this write when it arrives; the write is idempotent.
    _apply_stripe_subscription(subscription)
    return _trial_start(subscription)


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
        sub = client.subscriptions.retrieve(row["stripe_subscription_id"])
        flagged = (sub.get("metadata") or {}).get(DELETION_FLAG) == "true"
        if closing and not sub.get("cancel_at_period_end"):
            params = {"cancel_at_period_end": True, "metadata": {DELETION_FLAG: "true"}}
            outcome = "stopped"
        elif not closing and flagged:
            # Stripe removes a metadata key that is set to an empty string.
            params = {"cancel_at_period_end": False, "metadata": {DELETION_FLAG: ""}}
            outcome = "restored"
        else:
            return "unchanged"
        sub = client.subscriptions.update(row["stripe_subscription_id"], params=params)
    except stripe.StripeError as exc:
        raise Problem(502, "stripe_error",
                      "We could not reach our payment provider, so nothing was changed. "
                      "Please try again in a moment.") from exc

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
        return SubscriptionOut(status="none")

    if row["status"] == "incomplete":
        refreshed = _refresh_from_stripe(account.id, row.get("stripe_customer_id"))
        if refreshed is not None:
            row = refreshed

    status = row["status"]
    return SubscriptionOut(
        status="none" if status == "incomplete" else status,
        plan=row["plan_slug"],
        trial_ends_at=_iso_dt(row["trial_end"]),
        current_period_end=_iso_dt(row["current_period_end"]),
        card_last4=None,
        cancel_at_period_end=bool(row["cancel_at_period_end"]),
    )


@router.post("/webhooks/stripe", summary="Stripe events", include_in_schema=True)
async def stripe_webhook(request: Request, stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None):
    """Authenticated by the signature header rather than by a bearer token.

    Delivery is at least once and events can arrive out of order, so every handler is
    idempotent: each writes the subscription's current state rather than a delta, so a
    repeated event lands the same value twice.

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
    obj = event["data"]["object"]

    try:
        if etype in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            # The event object is the subscription itself, carrying the status that matters.
            _apply_stripe_subscription(obj)
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
# without a fresh start. The plan slug is taken from the subscription metadata this service
# set when it created the subscription, and the price identifier is the fallback.
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
    meta = sub.get("metadata") or {}
    slug = meta.get("plan")
    if slug in PLANS:
        return slug
    price_id = _first_price_id(sub)
    if price_id:
        for candidate, plan in PLANS.items():
            if os.environ.get(plan.price_env_var) == price_id:
                return candidate
    return None


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


def _apply_stripe_subscription(sub) -> None:
    """Writes a Stripe subscription's current state through the one write path."""
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
    except stripe.StripeError:
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
