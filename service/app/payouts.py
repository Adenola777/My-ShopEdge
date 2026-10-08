"""Expected payouts: `getExpectedPayouts`, TikTok's unsettled transactions grouped by week.

Written 7 October 2026 from TikTok's own page for Get Unsettled Transactions, as the owner
pasted it the same day: the path, the scope, the query parameters, a request example sent by
GET, and a response example. Nothing here has been called against a real shop yet.
**Unverified against TikTok** until the first seller opens the screen. In particular:

- The response example is in USD with whole-number amounts ("100", "130"). This reads every
  amount as a decimal string in the currency's major unit, the way the statement amounts on
  real GB statements arrive ("458.38"), and refuses any currency other than GBP.
- `estimated_settlement` arrives in the example as a string of Unix seconds ("1685548800").
  A transaction whose value is empty, zero or not a number has no week, so it is left out of
  the weeks and the total and counted in the log. How often TikTok sends one is unknown.
- TikTok's page says the endpoint returns only transactions created after 1 January 2025,
  that a transaction leaves the list once it is settled, and that every amount is an
  estimate. The contract's `confidence` is therefore always `estimated`.

The read happens when the seller asks, not in the daily sync, so the figure is as fresh as
TikTok's and no table holds a copy. The page sends this request on every view, which costs
one TikTok call per hundred unsettled transactions.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .auth import Account, require_account
from .dates import LONDON, now_utc
from .db import tenant
from .money import Money, money
from .problems import Problem
from .shops import require_shop
from .tiktok_api import TikTokError, client_for
from .tiktok_sync import pence

log = logging.getLogger(__name__)

router = APIRouter(tags=["Money"])

UNSETTLED_PATH = "/finance/202507/orders/unsettled"

# A seller with more than this many pages of unsettled transactions is refused rather than
# shown a total that silently leaves the rest out. At 100 a page this is 5,000 transactions.
MAX_PAGES = 50


class PayoutWeek(BaseModel):
    week_starting: date
    amount: Money
    orders: int


class ExpectedPayouts(BaseModel):
    as_of: datetime
    confidence: str
    total: Money
    weeks: list[PayoutWeek]


def _monday(moment: datetime) -> date:
    """The Monday of the London week the moment falls in, as `ledger_entries.basis_week`."""
    day = moment.astimezone(LONDON).date()
    return day - timedelta(days=day.weekday())


def _settles_at(value: Any) -> datetime | None:
    try:
        seconds = int(str(value))
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(seconds, timezone.utc) if seconds > 0 else None


def group_by_week(transactions: list[dict[str, Any]], currency: str = "GBP") -> tuple[list[PayoutWeek], int]:
    """Sums `est_settlement_amount` by the London week of `estimated_settlement`.

    `orders` counts distinct `order_id` values among transactions of type ORDER, so an
    adjustment moves a week's amount without adding an order to it. Returns the weeks in date
    order and the number of transactions left out because they carried no date.
    """
    amounts: dict[date, int] = defaultdict(int)
    orders: dict[date, set[str]] = defaultdict(set)
    undated = 0
    for txn in transactions:
        if (txn.get("currency") or currency) != currency:
            raise Problem(502, "tiktok_currency",
                          f"TikTok sent an unsettled amount in {txn.get('currency')}, "
                          f"and this shop sells in {currency}, so the expected payouts cannot be shown.")
        when = _settles_at(txn.get("estimated_settlement"))
        if when is None:
            undated += 1
            continue
        week = _monday(when)
        amounts[week] += pence(txn.get("est_settlement_amount"), currency)
        if txn.get("type") == "ORDER" and txn.get("order_id"):
            orders[week].add(str(txn["order_id"]))
    weeks = [PayoutWeek(week_starting=w, amount=money(amounts[w], currency), orders=len(orders[w]))
             for w in sorted(amounts)]
    return weeks, undated


def read_unsettled(client) -> list[dict[str, Any]]:
    """Every unsettled transaction TikTok holds for the shop, oldest order first."""
    found: list[dict[str, Any]] = []
    for n, page in enumerate(client.pages(
            "GET", UNSETTLED_PATH,
            {"sort_field": "order_create_time", "sort_order": "ASC"}), start=1):
        found.extend(page.get("transactions") or [])
        if n >= MAX_PAGES and page.get("next_page_token"):
            raise Problem(502, "too_many_unsettled",
                          "TikTok holds more unsettled transactions than MyShopEdge can total "
                          "here, so no figure is shown rather than a partial one. Your "
                          "figures in Money are unaffected.")
    return found


@router.get("/shops/{shopId}/payouts/expected", response_model=ExpectedPayouts,
            summary="Unsettled orders by estimated week")
def get_expected_payouts(
    account: Annotated[Account, Depends(require_account)],
    shop_id: Annotated[UUID, Depends(require_shop)],
) -> ExpectedPayouts:
    with tenant(account.id) as conn:
        row = conn.execute("select currency from shops where id = %s", (str(shop_id),)).fetchone()
        currency = (row[0] if row and row[0] else "GBP")
        try:
            client = client_for(conn, shop_id)
        except TikTokError as err:
            raise Problem(409, "not_connected",
                          "This shop is not connected to TikTok, so there is nothing to read.") from err

    as_of = now_utc()
    try:
        transactions = read_unsettled(client)
    except TikTokError as err:
        log.warning("unsettled read for shop %s refused: %s %s", shop_id, err.code, err.message)
        raise Problem(502, "tiktok_error",
                      "TikTok did not answer just now, so no expected payouts are shown. "
                      "Try again in a few minutes.") from err

    weeks, undated = group_by_week(transactions, currency)
    if undated:
        log.warning("unsettled read for shop %s: %d transaction(s) carried no estimated date",
                    shop_id, undated)
    total = sum(w.amount.amount_minor for w in weeks)
    return ExpectedPayouts(as_of=as_of, confidence="estimated", total=money(total, currency),
                           weeks=weeks)
