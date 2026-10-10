"""What each plan may use. Built 10 October 2026 from the owner's "MyShopEdge Final Pricing
Packaging and Code Command", which the owner told this session to build that day.

WHERE THE PLAN COMES FROM

The plan is `subscriptions.plan_slug`, which only `billing._apply_stripe_subscription` writes,
from the Stripe subscription's price identifier, on a verified webhook or on a read back from
Stripe. A browser never sends a plan here, and nothing in this module reads one from a request.

ACCESS BY ACCOUNT STATE (A36, the owner's ruling of 10 October 2026)

The owner first chose that an account with no live plan keeps everything (A35.1). Later the
same day he ruled that the accounts without a plan are test accounts and that the brief's
billing access rule applies from now on. `access_for_row` gives one of three answers:

  * `full`: a status in `billing.LIVE` (trialing, active, past_due) with a known plan. The
    plan's features below apply.
  * `none`: no subscription row, or one still `incomplete`. The seller may watch the import,
    choose a plan and disconnect, and nothing else (`shop_access`). The service answers
    403 `trial_required`.
  * `read_only`: `canceled`, which covers an ended trial or plan. The figures stay readable
    with the features of the plan the account last held, less exports, and nothing can be
    changed. The service answers 403 `plan_ended` to a write or an export.

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
# What an ended plan can no longer do, because each makes something new.
EXPORTING = frozenset({"exports", "scheduled_exports", "export_history"})


def access_for_row(row: dict | None) -> str:
    """`full`, `none` or `read_only`, as the module's docstring sets out."""
    status = (row or {}).get("status")
    if status in LIVE and row.get("plan_slug") in PLANS:
        return "full"
    if status == "canceled":
        return "read_only"
    return "none"


def features_for_row(row: dict | None) -> frozenset[str]:
    """The features a subscription row grants."""
    access = access_for_row(row)
    if access == "full":
        return BY_PLAN[row["plan_slug"]]
    if access == "read_only":
        return BY_PLAN.get(row.get("plan_slug") or "", frozenset()) - EXPORTING
    return frozenset()


# The shop routes a seller with no trial may use: the import's progress, disconnecting, and
# the alert settings the Settings page reads. Matched on the method and the end of the path.
ONBOARDING_ROUTES = (("GET", "/sync"), ("DELETE", "/connection"),
                     ("GET", "/alert-settings"), ("PUT", "/alert-settings"))
# Paths an ended plan may not read either, because each builds or lists files.
EXPORT_PATHS = ("/exports", "/export-schedules", "/cost-uploads")


def shop_access(row: dict | None, method: str, path: str) -> None:
    """Raises the right 403 when the account's state does not allow this shop request."""
    access = access_for_row(row)
    if access == "full":
        return
    tail = path.rstrip("/")
    if any(method == m and tail.endswith(end) for m, end in ONBOARDING_ROUTES):
        return
    if access == "none":
        raise Problem(403, "trial_required",
                      "Start your 30-day free trial to see your shop's figures. Your shop "
                      "stays connected, and nothing has been charged.")
    if method != "GET" or any(p in tail for p in EXPORT_PATHS):
        raise Problem(403, "plan_ended",
                      "Your plan has ended, so your figures can be read but nothing can be "
                      "changed or exported. Choose a plan to carry on.")


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
