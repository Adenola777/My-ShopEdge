"""What each plan may use. Built 10 October 2026 (A35) and rebuilt 11 October 2026 to the
owner's pricing and checkout specification (A38), which adds Explorer and moves product costs
and gross profit onto every plan.

WHERE THE PLAN COMES FROM

The plan is `subscriptions.plan_slug`, which only `billing._apply_stripe_subscription` writes,
from the Stripe subscription's price identifier, on a verified webhook or on a read back from
Stripe. A browser never sends a plan here, and nothing in this module reads one from a request.

ACCESS BY ACCOUNT STATE

`access_for_row` gives one of three answers:

  * `full`: a status in `billing.LIVE` (trialing, active, past_due) with a paid plan. That
    plan's features apply.
  * `explorer`: no subscription row, or one still `incomplete`. Since A38 such an account is
    on Explorer, the free plan, and sees its figures with Explorer's features. It replaces
    A36's `none`, which closed every figure until a trial started.
  * `read_only`: `canceled`, which covers an ended trial or plan. The figures stay readable
    with the features of the plan the account last held, less exports, and nothing can be
    changed. The service answers 403 `plan_ended` to a write or an export.

WHAT EACH PLAN HOLDS (A38.2)

  * Explorer: product costs, uploaded or typed, and gross profit.
  * Starter: adds gross margin, the orders behind a figure and the full payout explanation.
  * Growth: adds exports, the VAT threshold tracker and the cash basis.
  * Pro: adds scheduled exports, export history and the payout review list.

A seller's own copy of their data (`/me/export`) is not a plan feature. It is the seller's
right under data protection law, so every plan keeps it.

**Unverified against a real seller on each plan.** Production held one subscription on
11 October 2026, a Starter trial. The gating has run in the smoke test and against the local
copy only.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from . import db
from .auth import Account, require_account
from .billing import LIVE
from .problems import Problem

# Each feature, the plan that first holds it, and the sentence a refused request carries.
FEATURES: dict[str, tuple[str, str]] = {
    "costs": ("explorer", "Product costs are on every plan."),
    "profit": ("explorer", "Gross profit is on every plan."),
    "margin": ("starter", "Gross margin by product is available on Starter."),
    "drilldown": ("starter", "The orders behind a figure are available on Starter."),
    "payout_detail": ("starter", "Full payout explanations are available on Starter."),
    "exports": ("growth", "Exports are available on Growth."),
    "vat": ("growth", "The VAT threshold tracker is available on Growth."),
    "basis": ("growth", "The cash basis is available on Growth."),
    "scheduled_exports": ("pro", "Scheduled exports are available on Pro."),
    "export_history": ("pro", "Export history is available on Pro."),
    "priority_review": ("pro", "The payout review list is available on Pro."),
}

_RANK = {"explorer": 0, "starter": 1, "growth": 2, "pro": 3}
BY_PLAN: dict[str, frozenset[str]] = {
    plan: frozenset(f for f, (first, _) in FEATURES.items() if _RANK[first] <= rank)
    for plan, rank in _RANK.items()
}
ALL = BY_PLAN["pro"]
# What an ended plan can no longer do, because each makes something new.
EXPORTING = frozenset({"exports", "scheduled_exports", "export_history"})


def access_for_row(row: dict | None) -> str:
    """`full`, `explorer` or `read_only`, as the module's docstring sets out."""
    status = (row or {}).get("status")
    if status in LIVE and row.get("plan_slug") in BY_PLAN:
        return "full"
    if status == "canceled":
        return "read_only"
    return "explorer"


def plan_for_row(row: dict | None) -> str:
    """The plan whose limits and features apply: the paid plan while it is live, and
    Explorer otherwise. An ended plan keeps its features for reading (`features_for_row`) but
    its limits are Explorer's, because nothing new is bought on it."""
    if access_for_row(row) == "full":
        return row["plan_slug"]
    return "explorer"


def features_for_row(row: dict | None) -> frozenset[str]:
    """The features a subscription row grants."""
    access = access_for_row(row)
    if access == "full":
        return BY_PLAN[row["plan_slug"]]
    if access == "read_only":
        return BY_PLAN.get(row.get("plan_slug") or "", BY_PLAN["explorer"]) - EXPORTING
    return BY_PLAN["explorer"]


# Paths an ended plan may not read either, because each builds or lists files.
EXPORT_PATHS = ("/exports", "/export-schedules", "/cost-uploads")
# The shop routes an ended plan may still change: disconnecting, and the alert settings.
ENDED_WRITES = (("DELETE", "/connection"), ("PUT", "/alert-settings"))


def shop_access(row: dict | None, method: str, path: str) -> None:
    """Raises 403 `plan_ended` when an ended plan asks to change or export something.
    Explorer and a live plan pass; their features are checked by each route."""
    if access_for_row(row) != "read_only":
        return
    tail = path.rstrip("/")
    if any(method == m and tail.endswith(end) for m, end in ENDED_WRITES):
        return
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
