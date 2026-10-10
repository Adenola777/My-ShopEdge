"""What each plan may use. Built 10 October 2026 from the owner's "MyShopEdge Final Pricing
Packaging and Code Command", which the owner told this session to build that day.

WHERE THE PLAN COMES FROM

The plan is `subscriptions.plan_slug`, which only `billing._apply_stripe_subscription` writes,
from the Stripe subscription's price identifier, on a verified webhook or on a read back from
Stripe. A browser never sends a plan here, and nothing in this module reads one from a request.

WHO IS LIMITED

Only a live plan limits anything: a status in `billing.LIVE` (trialing, active, past_due) and a
slug in `plans.PLANS`. An account with no subscription row, or one whose plan is incomplete or
cancelled, keeps every feature. The owner chose that on 10 October 2026 ("Everything, as
today"), so that nobody who signed up before the tiers existed loses a screen, and so that a
seller between plans is not shut out of their own figures.

WHAT EACH PLAN HOLDS

  * Starter: none of the features below. It keeps the Overview, the net proceeds chain,
    payouts and statements, refunds and returns, products ranked by net proceeds and the VAT
    threshold, none of which is gated.
  * Growth: costs, profit, drilldown, exports and basis.
  * Pro: everything in Growth, plus scheduled_exports, export_history and priority_review.

A seller's own copy of their data (`/me/export`) is not a plan feature. It is the seller's
right under data protection law, so every plan keeps it.

**Unverified against a real Starter seller.** Production held one subscription when queried on
10 October 2026, a Starter trial. The gating has run in the smoke test and against the local
copy only.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from . import db
from .auth import Account, require_account
from .billing import LIVE
from .plans import PLANS
from .problems import Problem

# Each feature, the plan that first holds it, and the sentence a refused request carries.
FEATURES: dict[str, tuple[str, str]] = {
    "costs": ("growth", "Product costs come with the Growth plan."),
    "profit": ("growth", "Gross profit and margin come with the Growth plan."),
    "drilldown": ("growth", "The transactions behind a figure come with the Growth plan."),
    "exports": ("growth", "Exports come with the Growth plan."),
    "basis": ("growth", "The cash basis comes with the Growth plan."),
    "scheduled_exports": ("pro", "Scheduled exports come with the Pro plan."),
    "export_history": ("pro", "Export history comes with the Pro plan."),
    "priority_review": ("pro", "The payout review list comes with the Pro plan."),
}

ALL = frozenset(FEATURES)
GROWTH = frozenset(f for f, (plan, _) in FEATURES.items() if plan == "growth")
BY_PLAN: dict[str, frozenset[str]] = {"starter": frozenset(), "growth": GROWTH, "pro": ALL}


def features_for_row(row: dict | None) -> frozenset[str]:
    """The features a subscription row grants. No live plan grants every feature."""
    if row is None or row.get("status") not in LIVE or row.get("plan_slug") not in PLANS:
        return ALL
    return BY_PLAN[row["plan_slug"]]


def features_for(account_id) -> frozenset[str]:
    return features_for_row(db.get_subscription_row(account_id))


def refuse(feature: str) -> Problem:
    plan, detail = FEATURES[feature]
    return Problem(403, "plan_upgrade_required", detail,
                   {"required_plan": plan, "feature": feature})


def check(account_id, feature: str) -> None:
    if feature not in features_for(account_id):
        raise refuse(feature)


def require(feature: str) -> Callable[..., None]:
    """A route dependency that answers 403 plan_upgrade_required when the plan lacks it."""
    if feature not in FEATURES:
        raise ValueError(feature)

    def dependency(account: Annotated[Account, Depends(require_account)]) -> None:
        check(account.id, feature)

    return dependency


def require_basis(account_id, basis: str) -> None:
    """The sales basis is on every plan. The cash basis is the `basis` feature."""
    if basis == "cash":
        check(account_id, "basis")
