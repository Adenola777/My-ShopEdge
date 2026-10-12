"""Creates the nine A38 prices, three cycles for each paid plan, from app/plans.py.

Rewritten 11 October 2026, when the owner approved the nine amounts of A38.1 and asked for all
nine to be created. **It has run only against a stand-in client**, because no Stripe key reaches
the session (CLAUDE.md rule 2). It is the owner's to run, in his own terminal:

    STRIPE_SECRET_KEY=sk_live_... python3 scripts/setup_stripe.py            # shows the plan
    STRIPE_SECRET_KEY=sk_live_... I_MEAN_LIVE=yes python3 scripts/setup_stripe.py --apply

Without --apply it reads the account and says what it would create, and creates nothing.

What it does, and what it never does.

- It finds each plan's product by `metadata['plan']`. With a live key it never creates a
  product; if one is missing it stops, because CLAUDE.md rule 3 asks for an explicit
  instruction for each product in the live account and the owner's of 11 October 2026 named
  prices only. With a test key it creates a missing product.
- Each price carries the lookup key `myshopedge_<plan>_<cycle>_a38`. A price already holding
  its key with the same amount and interval is reused, so running it twice creates nothing the
  second time. One holding the key with a different amount stops the script.
- It never archives or changes a price. The three prices sold before A38 stay as they are, and
  the one live subscription on the old Starter price keeps it (A38.5).
- Annual, billed monthly is an ordinary monthly price. Its twelve-payment term is kept by the
  service (A38.6), not by Stripe's price.

The secret key is read from the environment. It is never printed and never written to a file.
The output is the nine environment variables to set on the service.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import stripe  # noqa: E402

from app.plans import CYCLES, PAID, PLANS, TRIAL_DAYS  # noqa: E402

CURRENCY = "gbp"
CYCLE_NAMES = {"annual": "Annual prepaid", "annual_monthly": "Annual, billed monthly",
               "monthly": "Monthly"}


def lookup_key(slug: str, cycle: str) -> str:
    return f"myshopedge_{slug}_{cycle}_a38"


def main(argv: list[str]) -> int:
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        print("STRIPE_SECRET_KEY is not set.", file=sys.stderr)
        return 1
    apply = "--apply" in argv
    live = key.startswith(("sk_live_", "rk_live_"))
    if live and apply and os.environ.get("I_MEAN_LIVE") != "yes":
        print("This is a live key. Set I_MEAN_LIVE=yes to create real prices.", file=sys.stderr)
        return 1
    print(f"{'Live' if live else 'Test'} account. {'Creating' if apply else 'Showing'} the nine A38 prices.\n")

    client = stripe.StripeClient(key)
    # Every product is found before anything is created, so a missing one stops the run with
    # nothing half done.
    products = {slug: _find_product(client, slug) for slug in PAID}
    missing = [slug for slug, product in products.items() if product is None]
    if live and missing:
        print(f"No product carries metadata plan={', '.join(missing)} in the live account. Nothing "
              "was created. Creating a product needs the owner's instruction (rule 3).",
              file=sys.stderr)
        return 1
    results: list[tuple[str, str]] = []
    for slug in PAID:
        plan = PLANS[slug]
        product = products[slug]
        if product is None:
            if not apply:
                print(f"{plan.name:<8} product would be created")
                product_id = "(new product)"
            else:
                product_id = client.products.create(
                    params={"name": f"MyShopEdge {plan.name}", "metadata": {"plan": slug}}).id
        else:
            product_id = product.id
        for cycle in CYCLES:
            price = plan.prices[cycle]
            want = {"unit_amount": price.charge_minor, "interval": price.interval}
            existing = _find_price(client, lookup_key(slug, cycle))
            label = f"{plan.name:<8} {CYCLE_NAMES[cycle]:<23} £{price.charge_minor / 100:>7.2f} a {price.interval}"
            if existing is not None:
                got = {"unit_amount": existing.unit_amount, "interval": existing.recurring.interval}
                if got != want or existing.currency != CURRENCY:
                    print(f"{label}: {existing.id} holds the key with {got}. Stopped; nothing more "
                          "was created.", file=sys.stderr)
                    return 1
                print(f"{label}  {existing.id}  already exists")
                results.append((price.env_var, existing.id))
                continue
            if not apply:
                print(f"{label}  would be created")
                continue
            created = client.prices.create(params={
                "product": product_id,
                "currency": CURRENCY,
                "unit_amount": price.charge_minor,
                "recurring": {"interval": price.interval, "interval_count": 1, "usage_type": "licensed"},
                # Exclusive, as the three prices of 23 September are. No VAT is charged while
                # Inspirecraft Global Ltd is not VAT registered (A15.6, A38.1).
                "tax_behavior": "exclusive",
                "lookup_key": lookup_key(slug, cycle),
                "nickname": f"{plan.name}, {CYCLE_NAMES[cycle]}",
                "metadata": {"plan": slug, "cycle": cycle, "payments": str(price.payments)},
            })
            print(f"{label}  {created.id}  created")
            results.append((price.env_var, created.id))

    if not apply:
        print("\nNothing was created. Run again with --apply to create the prices marked above.")
        return 0
    print(f"\nThe {TRIAL_DAYS}-day trial is set on the subscription, not on the price.")
    print("Set these nine on My-ShopEdge-1 (and the sync cron if it reads plans):\n")
    for env_var, price_id in results:
        print(f"{env_var}={price_id}")
    return 0


def _find_product(client: stripe.StripeClient, slug: str):
    found = client.products.search(params={"query": f"metadata['plan']:'{slug}' AND active:'true'", "limit": 1})
    return found.data[0] if found.data else None


def _find_price(client: stripe.StripeClient, key: str):
    found = client.prices.list(params={"lookup_keys": [key], "limit": 1})
    return found.data[0] if found.data else None


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
