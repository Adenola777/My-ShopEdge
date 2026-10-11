"""The four plans and their three billing cycles, and the single place they are defined.

Rewritten on 11 October 2026 to the owner's pricing and checkout specification (A38): Explorer,
free with no card, and Starter, Growth and Pro, each sold Annual prepaid, Annual billed monthly
or Monthly. It replaces the three plans of A35.

A plan's price is never sent by a browser. The browser sends a slug and a cycle, the service
looks both up here, and it uses the Stripe price identifier held in that cycle's environment
variable. A request carrying a price identifier is ignored. **No new price exists in Stripe.**
The owner ruled on 11 October 2026 that checkout stays off until he approves each price
(A38.3), so the nine `STRIPE_PRICE_<PLAN>_<CYCLE>` variables are unset and a checkout answers
503 `plan_unavailable`. Each plan's `legacy_env_var` holds the price sold before A38, so a
subscription already on it is still recognised as that plan.

What each plan may use is enforced in ``entitlements.py``. The lists below are the words a
seller reads. ``coming_soon`` holds features the owner's specification places in a plan that
the product does not have yet (A38.3 answer 2); they are shown labelled Coming soon and never
as included.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The owner ruled on 7 October 2026 that the beta trial is thirty days. Whether a paid plan
# keeps a trial under A38 is not ruled (A38.5), so checkout keeps it until he says otherwise.
TRIAL_DAYS = 30

# The three billing cycles, in the order the selector shows them. Annual prepaid is the
# default, because it is the best value (A38.1).
CYCLES = ("annual", "annual_monthly", "monthly")
DEFAULT_CYCLE = "annual"


@dataclass(frozen=True)
class Price:
    """One cycle's price, in whole pence (A13 rule 3).

    `charge_minor` is what one payment takes, `per_month_minor` the monthly figure the card
    shows, and `payments` how many payments a term holds."""
    charge_minor: int
    per_month_minor: int
    payments: int
    interval: str             # "year" or "month"
    env_var: str


@dataclass(frozen=True)
class Plan:
    slug: str
    name: str
    audience: str
    shop_limit: int
    order_limit: int | None   # None is unlimited
    history_days: int | None  # None is unlimited
    highlight: bool
    prices: dict[str, Price] = field(default_factory=dict)
    legacy_env_var: str | None = None
    features: list[str] = field(default_factory=list)
    coming_soon: list[str] = field(default_factory=list)

    @property
    def free(self) -> bool:
        return not self.prices


def _prices(slug: str, annual: int, annual_monthly: int, monthly: int) -> dict[str, Price]:
    up = slug.upper()
    return {
        # £190 a year shows as £15.83 a month, rounded half up to the penny.
        "annual": Price(annual, (annual * 100 // 12 + 50) // 100, 1, "year",
                        f"STRIPE_PRICE_{up}_ANNUAL"),
        "annual_monthly": Price(annual_monthly, annual_monthly, 12, "month",
                                f"STRIPE_PRICE_{up}_ANNUAL_MONTHLY"),
        "monthly": Price(monthly, monthly, 1, "month", f"STRIPE_PRICE_{up}_MONTHLY"),
    }


PLANS: dict[str, Plan] = {
    "explorer": Plan(
        slug="explorer",
        name="Explorer",
        audience="For new sellers getting started.",
        shop_limit=1,
        order_limit=100,
        history_days=30,
        highlight=False,
        features=[
            "1 TikTok Shop",
            "Up to 100 orders/month",
            "Net proceeds and where the money went",
            "Upload product costs",
            "Gross profit where costs are added",
            "Basic payout status",
            "Last 30 days of data",
        ],
    ),
    "starter": Plan(
        slug="starter",
        name="Starter",
        audience="For serious single-shop sellers.",
        shop_limit=1,
        order_limit=500,
        history_days=365,
        highlight=False,
        prices=_prices("starter", 19000, 1725, 1900),
        legacy_env_var="STRIPE_PRICE_STARTER",
        features=[
            "1 TikTok Shop",
            "Up to 500 orders/month",
            "Full product profit and margin",
            "Cost coverage and missing-cost alerts",
            "Full payout explanations",
            "Return and write-off treatment",
            "12 months of data",
        ],
    ),
    "growth": Plan(
        slug="growth",
        name="Growth",
        audience="For growing sellers who need exports and multi-shop control.",
        shop_limit=3,
        order_limit=1000,
        history_days=730,
        highlight=True,
        prices=_prices("growth", 39000, 3542, 3900),
        legacy_env_var="STRIPE_PRICE_GROWTH",
        features=[
            "Up to 3 TikTok Shops",
            "Up to 1,000 orders/month",
            "All Starter features",
            "Product profit and reconciliation exports",
            "Accountant-ready CSV/XLSX",
            "VAT threshold tracker",
            "24 months of data",
        ],
        coming_soon=["Multi-shop consolidated view", "1 accountant seat"],
    ),
    "pro": Plan(
        slug="pro",
        name="Pro",
        audience="For agencies, accountants and high-volume sellers.",
        shop_limit=10,
        order_limit=None,
        history_days=None,
        highlight=False,
        prices=_prices("pro", 79000, 7208, 7900),
        legacy_env_var="STRIPE_PRICE_PRO",
        features=[
            "Up to 10 TikTok Shops",
            "Unlimited orders",
            "All Growth features",
            "Unlimited data history",
        ],
        coming_soon=["Client workspaces", "Up to 5 accountant/team seats", "Priority support"],
    ),
}

PAID = ("starter", "growth", "pro")
PLAN_ORDER = ["explorer", "starter", "growth", "pro"]

# Rows from the commercial price sheet of 22 September 2026 that the MVP does not have.
# None of these is served to a client. Each needs a specification, a schema change and a
# test before it can be sold.
# Ruled out of the MVP on 22 September 2026. These are not pending decisions any more.
# They are recorded here so that nobody advertises them and nobody quietly builds them.
OUT_OF_MVP = [
    "Expense tracking. The product does not collect overheads, ruled in A8. There is no "
    "table, screen or endpoint.",
    "Multiple channels besides TikTok Shop. Several TikTok Shops per account are allowed by "
    "plan since A38 (11 October 2026).",
    "Profit and loss reporting. It appears nowhere in the specification pack.",
    "Advanced analytics. Nothing is named, so nothing can be built or tested.",
]

# Kept under the old name so nothing that imports it breaks.
PENDING_SCOPE = OUT_OF_MVP

# Ruled in on 22 September 2026, and not built yet. Unlike the list above, these are work.
#
# The order limit was ruled soft in A16.3 and built on 9 October 2026 (order_usage.py): the
# account's orders in its billing period are counted, Today shows the count at 80 and 100 per
# cent beside the larger plan, and one in-app notice is written per period at 100 per cent.
# Two parts of A16.3 remain, and they are listed below.
IN_SCOPE_NOT_BUILT = [
    "The email A16.3 sends at 100 per cent of the order limit. Nothing in the service can send "
    "email and no provider has been chosen, so an in-app notice is written in its place.",
]
