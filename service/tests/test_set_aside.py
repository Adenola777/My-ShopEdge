"""The set-aside method of A30.3, on rules made up for the test.

The figures below are round numbers chosen so each case can be worked by hand. They are
not HMRC's and must never be loaded as reference rules. The test checks the method only:
the allowance, its taper, the bands in order, and the two Class 4 rates.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tax import _estimate, _tax_year_start  # noqa: E402

RULES = {
    "income_tax_personal_allowance": {"amount_minor": 1_000_000, "taper_from_minor": 10_000_000, "taper_ratio": 2},
    "income_tax_bands": {"bands": [{"width_minor": 3_000_000, "rate_bp": 2000},
                                   {"width_minor": 7_000_000, "rate_bp": 4000},
                                   {"width_minor": None, "rate_bp": 4500}]},
    "class4_nic": {"lower_minor": 1_000_000, "upper_minor": 5_000_000, "main_rate_bp": 600, "upper_rate_bp": 200},
}

CASES = [
    # (profit, allowance, income tax, class 4, why)
    (-50_000, 1_000_000, 0, 0, "a loss owes nothing"),
    (800_000, 1_000_000, 0, 0, "under the allowance and the lower limit"),
    (2_000_000, 1_000_000, 200_000, 60_000, "10,000 at 20%; 10,000 at 6%"),
    (6_000_000, 1_000_000, 600_000 + 800_000, 240_000 + 20_000,
     "30,000 at 20% and 20,000 at 40%; 40,000 at 6% and 10,000 at 2%"),
    (11_000_000, 500_000, 600_000 + 2_800_000 + 225_000, 240_000 + 120_000,
     "allowance tapered by 5,000; 30,000, 70,000 and 5,000 taxed; class 4 as before plus 60,000 at 2%"),
    (13_000_000, 0, 600_000 + 2_800_000 + 1_350_000, 240_000 + 160_000,
     "allowance tapered away; 30,000 left at 45%"),
    (1_000_003, 1_000_000, 1, 0, "3p at 20% rounds to 1p; nothing above the lower limit"),
]

failed = 0
for profit, pa, tax, c4, why in CASES:
    got = _estimate(profit, RULES)
    ok = got == (pa, tax, c4)
    failed += not ok
    print(("PASS " if ok else "FAIL ") + f"{profit}: {got} expected {(pa, tax, c4)} ({why})")

for day, start in [(date(2026, 4, 5), date(2025, 4, 6)), (date(2026, 4, 6), date(2026, 4, 6)),
                   (date(2026, 9, 28), date(2026, 4, 6)), (date(2027, 1, 1), date(2026, 4, 6))]:
    ok = _tax_year_start(day) == start
    failed += not ok
    print(("PASS " if ok else "FAIL ") + f"tax year of {day} starts {_tax_year_start(day)}")

if failed:
    print(f"{failed} failure(s)")
    sys.exit(1)
print("every set-aside case held")
