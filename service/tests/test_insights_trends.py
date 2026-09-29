"""The two insight rules of A31.1 and the months behind the trend bars.

The postage case is the QA document's own (DSH-6): "Clay Mask: postage and packing £2.51 on
£9.25; stock £3.20. Insight states postage share 27p in the £1; no claim that posting costs
more than making." The loss case uses round made-up numbers that can be worked by hand.

    python3 tests/test_insights_trends.py
"""

import os
import sys
from datetime import date
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NEON_AUTH_JWKS_URL", "http://127.0.0.1:1/jwks.json")
os.environ.setdefault("NEON_AUTH_AUDIENCE", "test")
os.environ.setdefault("NEON_AUTH_ISSUER", "https://test.invalid")

from app.insights import EvidencePeriod, build  # noqa: E402
from app.trends import _months  # noqa: E402

failed = 0


def check(ok, what):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + what)


period = EvidencePeriod(from_="2026-09-01", to="2026-09-29", basis="sales")


def row(title, units, net_proceeds, cost, without_cost=0):
    return {"product_id": uuid4(), "title": title, "units_sold": units, "skus_without_cost": without_cost,
            "cost_retained_minor": cost, "net_proceeds_minor": net_proceeds}


mask = row("Clay Mask", 1, 690, 320)
got = build([mask], {mask["product_id"]: {"net_sales_minor": 925, "pp_minor": 251, "skus_without_pp": 0}},
            period, "GBP")
share = [i for i in got if i.rule_key == "postage_share"]
check(len(share) == 1 and "27p of every £1" in share[0].headline, f"Clay Mask reads 27p in the £1: {share[0].headline if share else got}")
check(not any("more than" in (i.headline + (i.detail or "")) for i in share), "no claim that posting costs more than making")
check(all(v.label for v in share[0].evidence.values) and share[0].evidence.entity_type == "product",
      "the evidence carries every figure and names the product")
check(not [i for i in got if i.rule_key == "negative_contribution"], "Clay Mask made money, so no loss insight")

loser = row("Glass Jar", 4, 1000, 1400)
got = build([loser], {}, period, "GBP")
loss = [i for i in got if i.rule_key == "negative_contribution"]
check(len(loss) == 1 and "lost £4.00 on 4 units" in loss[0].headline, f"a loss of £4.00 on 4 units: {loss[0].headline if loss else got}")
check("Options:" in (loss[0].detail or ""), "the loss insight offers options rather than an instruction")
contribution = [v for v in loss[0].evidence.values if v.label == "Contribution"][0]
check(contribution.amount.amount_minor == -400, "the evidence shows the contribution the headline states")
check(not [i for i in got if i.rule_key == "postage_share"], "no postage figures, so no postage insight")

uncosted = row("Mystery Box", 3, 500, None, without_cost=1)
check(build([uncosted], {uncosted["product_id"]: {"net_sales_minor": 900, "pp_minor": 300, "skus_without_pp": 0}},
            period, "GBP") == [], "a product without a cost gets no insight at all")

partial = row("Half Known", 2, 2000, 500)
check([i.rule_key for i in build([partial], {partial["product_id"]: {"net_sales_minor": 2000, "pp_minor": 200,
                                                                     "skus_without_pp": 1}}, period, "GBP")] == [],
      "a variant sold with no postage figure makes the postage share unknown")

months = _months(date(2026, 9, 29))
check(len(months) == 12 and months[0] == (date(2025, 10, 1), date(2025, 10, 31))
      and months[-1] == (date(2026, 9, 1), date(2026, 9, 30)), f"twelve months, October to September: {months[0]} .. {months[-1]}")
feb = [m for m in _months(date(2028, 3, 5)) if m[0].month == 2][0]
check(feb == (date(2028, 2, 1), date(2028, 2, 29)), "February in a leap year ends on the 29th")
jan = _months(date(2027, 1, 15))
check(jan[-1][0] == date(2027, 1, 1) and jan[-2][0] == date(2026, 12, 1), "the months cross the year end in order")

if failed:
    print(f"{failed} failure(s)")
    sys.exit(1)
print("every insight and trend case held")
