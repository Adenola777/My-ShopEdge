"""The pieces of a calculator line shared by Money and payout detail. Split from money_view
on 9 October 2026.

`settlements.py` needs them for payout detail's fee lines, and importing them from
money_view made a cycle: money_view imports products, products imports stock, and stock
imports settlements. CI's `test_set_aside.py`, which imports `tax` first, failed on it. This
module imports nothing from that cycle, so both can use it. money_view re-exports every name,
so existing imports from money_view keep working.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from pydantic import BaseModel

from .money import Money, money

TIKTOK_FEES = (
    "platform_commission", "affiliate_commission", "transaction_fee",
    "smart_promotions_fee", "shipping_fee", "return_handling_fee",
    "fbt_operations_fee", "fbt_shipping_fee", "fbt_storage_fee",
    "unmapped_fee", "platform_adjustment",
)

# A8.5's line names. A fee TikTok names that we do not recognise, and every platform
# adjustment, is shown under TikTok's own name instead.
LABELS = {
    "gross_sales": "Gross sales (GMV)",
    "seller_discount": "Seller discounts",
    "platform_commission": "Platform commission",
    "affiliate_commission": "Affiliate commission",
    "transaction_fee": "Transaction fee",
    "smart_promotions_fee": "Smart Promotions fee",
    "shipping_fee": "Shipping fee",
    "return_handling_fee": "Return handling fee",
    "fbt_operations_fee": "FBT operations fee",
    "fbt_shipping_fee": "FBT shipping fee",
    "fbt_storage_fee": "FBT storage fee",
    "unmapped_fee": "Fee MyShopEdge does not recognise",
    "platform_adjustment": "TikTok adjustment",
    "refund": "Refunds to customers",
    "cost_of_goods_sold": "Cost of goods sold",
    "seller_shipping": "Shipping and packaging you pay",
    "return_shipping": "Return shipping you paid",
    "stock_written_off": "Stock written off",
    # A18.3's names for the three figures that are not the same.
    "reserve_withheld": "Reserve withheld",
    "reserve_released": "Reserve released",
    "settlement": "Payout",
}
VERBATIM = ("unmapped_fee", "platform_adjustment")
# Categories that TikTok fills from more than one field (tiktok_sync.FEE_MAP and SHIP_MAP).
# Each field arrives as its own line, so under the category's name alone they read as
# duplicates: production showed "Affiliate commission" twice and "Shipping fee" three times
# on 10 October 2026. On the owner's instruction of that day each such line carries TikTok's
# own name for its field, as an unrecognised fee does. test_handlers_smoke checks this set
# against the two maps.
SHARED = ("affiliate_commission", "shipping_fee", "smart_promotions_fee", "return_shipping")


def tiktok_name(raw: str) -> str:
    """TikTok's own name for a fee or an adjustment, written as words.

    TikTok sends `live_specials_fee_amount` or `PLATFORM_PENALTY`, which a seller never sees
    in that form. On the owner's instruction of 10 October 2026 the label keeps TikTok's
    words and drops only the code formatting: the `_amount` ending and the underscores go,
    and the first letter alone is a capital. So "Live specials fee" and "Platform penalty".
    Nothing is translated or invented, and `tiktok_fee_type` still carries the string
    exactly as TikTok sent it.
    """
    name = raw[:-len("_amount")] if raw.lower().endswith("_amount") else raw
    words = " ".join(name.replace("_", " ").split()).lower()
    return words[:1].upper() + words[1:] if words else raw


def gross_margin(profit_minor: int | None, net_sales_minor: int) -> float | None:
    """Gross margin after returns as a fraction of net sales, to four places: 0.4752 is 47.52%.

    The owner's rulings of 10 October 2026: margin is gross profit after returns divided by
    net sales (the FAQ's definition), and it is unknown wherever that profit is unknown, so a
    missing cost never yields a margin. With no net sales there is nothing to divide by, and
    the margin is unknown too. The division is done in Decimal from whole pence (A13 rule 3);
    only the finished ratio becomes a float, because the contract types it as a number.
    """
    if profit_minor is None or net_sales_minor <= 0:
        return None
    ratio = (Decimal(profit_minor) / Decimal(net_sales_minor)).quantize(Decimal("0.0001"), ROUND_HALF_EVEN)
    return float(ratio)


def line_label(category: str, raw: str | None) -> str:
    """The name a line carries: TikTok's own words where the category alone is ambiguous."""
    if raw and (category in VERBATIM or category in SHARED):
        return tiktok_name(raw)
    return LABELS.get(category, category)


class CalculatorLine(BaseModel):
    label: str
    amount: Money
    category: str | None = None
    tiktok_field: str | None = None
    tiktok_fee_type: str | None = None



def _line(row: dict[str, Any], currency: str) -> CalculatorLine:
    """One ledger group as one line.

    `ledger_entries.tiktok_fee_type` holds TikTok's field name for a fee, for example
    `affiliate_ads_commission_amount`, and TikTok's adjustment type for a platform
    adjustment, for example `PLATFORM_PENALTY`. Checked on the development branch on 24
    September 2026. So it is the contract's `tiktok_field` for every fee, and its
    `tiktok_fee_type` for the two categories the contract says carry one. Two fees in the
    same category arrive as two lines, because no fee is merged with another.
    """
    category = row["category"]
    raw = row["tiktok_fee_type"]
    return CalculatorLine(
        label=line_label(category, raw),
        amount=money(int(row["amount_minor"]), currency),
        category=category,
        tiktok_field=raw if category != "platform_adjustment" else None,
        tiktok_fee_type=raw if category in VERBATIM else None,
    )
