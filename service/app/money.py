"""Money, as rule 3 of A13 requires it.

A figure is an integer of minor units with its currency beside it. No float ever holds an
amount. Where a calculation needs division, it goes through ``Decimal`` and comes back an
integer before it leaves the function.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field


class Money(BaseModel):
    amount_minor: int = Field(description="Integer minor units. 2084 is twenty pounds and eighty-four pence.")
    currency: str = Field(default="GBP", min_length=3, max_length=3)


def money(amount_minor: int, currency: str = "GBP") -> Money:
    return Money(amount_minor=amount_minor, currency=currency)


def from_decimal_string(value: str, currency: str = "GBP") -> Money:
    """Converts TikTok's string amounts, which arrive as '20.84', into minor units.

    TikTok returns amounts as strings with two decimals. Parsing them as floats loses
    pence, so they go through Decimal.
    """
    quantised = (Decimal(value) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return Money(amount_minor=int(quantised), currency=currency)


def per_unit(amount_minor: int, units: int) -> int:
    """One unit's share of an amount, rounded half away from zero to the penny.

    Integer floor division rounds a refund of -6000 over 22 units to -273 and a sale of
    34700 to 1577, so negative lines lean one way and positive lines the other. Decimal
    rounds both the same way.
    """
    share = (Decimal(amount_minor) / Decimal(max(units, 1))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(share)


def allocate(total: int, weights: list[int]) -> list[int]:
    """Largest remainder. The parts sum to the total exactly, with no residual pence.

    This is the rule that makes a three-unit order add up. Lifted from testdata/ingest.py,
    where the A12 assertions prove it, rather than written a second time.
    """
    if not weights or sum(weights) == 0:
        return [total] + [0] * (len(weights) - 1)
    total_weight = sum(weights)
    base = [total * w // total_weight for w in weights]
    remainder = total - sum(base)
    order = sorted(range(len(weights)), key=lambda i: -((total * weights[i]) % total_weight))
    step = 1 if remainder > 0 else -1
    for k in range(abs(remainder)):
        base[order[k % len(order)]] += step
    return base
