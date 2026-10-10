"""The pieces of a calculator line shared by Money and payout detail. Split from money_view
on 9 October 2026.

`settlements.py` needs them for payout detail's fee lines, and importing them from
money_view made a cycle: money_view imports products, products imports stock, and stock
imports settlements. CI's `test_set_aside.py`, which imports `tax` first, failed on it. This
module imports nothing from that cycle, so both can use it. money_view re-exports every name,
so existing imports from money_view keep working.
"""

from __future__ import annotations

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
    label = LABELS.get(category, category)
    if category in VERBATIM and raw:
        label = tiktok_name(raw)
    return CalculatorLine(
        label=label,
        amount=money(int(row["amount_minor"]), currency),
        category=category,
        tiktok_field=raw if category != "platform_adjustment" else None,
        tiktok_fee_type=raw if category in VERBATIM else None,
    )
