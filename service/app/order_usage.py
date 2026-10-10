"""The order count against the plan's limit. A16.3, soft enforcement. Built 9 October 2026.

WHAT IS COUNTED

Orders whose TikTok creation time (`orders.order_created_at`, set from TikTok's
`create_time` in `tiktok_sync.upsert_order`) falls in the subscription's current billing
period, `current_period_start` inclusive to `current_period_end` exclusive. A cancelled order
counts, because A16.3 says the work of reading it was done either way. The count is the
`order_quota` view from migration 0019, so the rule has one home in SQL and the limits have
one home in `plans.py`.

A16.3 says the count is taken "in Europe/London". Both ends of the period are instants that
Stripe sets, and `order_created_at` is an instant too, so comparing them gives the same answer
in any time zone. London decides only how the period's end is written for the seller.

PER ACCOUNT, ACROSS EVERY SHOP

The plan belongs to the account: `subscriptions.account_id` is unique (0018), and nothing
records a plan per shop. An account can hold more than one shop, because nothing in
`connections.py` stops a second one and the owner's own account holds two (CLAUDE.md, the
TikTok integration row). So the limit is applied per account, and the count covers every shop
the account owns, which is what `order_quota` already does by joining `shops.account_id`.
Today shows the same account figure on every shop's page.

WHEN NO USAGE IS SERVED

  * No subscription row, as A16.3 requires.
  * A status other than `trialing`, `active` or `past_due` (`billing.LIVE`). An `incomplete`
    row has not started and a `canceled` one has ended, so neither has a period to count in.
  * Either end of the period missing. Nothing is guessed in its place. Whether Stripe sends
    both ends for a subscription in trial is **unverified against this installation**: the
    demo loader writes both (`testdata/load_demo.py`), and `billing._sub_periods` reads them
    from the subscription or its first item, but no live trial row has been queried.
  * `now` outside the period. A period that has ended means the renewal has not reached the
    database yet, and counting the old period would show the seller a stale figure as current.

A trial counts as a period, because it carries a period like any other.

THE THRESHOLDS

`below` under 80 per cent, `approaching` from 80 per cent, `passed` from 100 per cent. Integer
arithmetic only, so 80 of 100 is approaching and 100 of 100 is passed. Nothing stops at either:
the sync, the figures and the exports carry on (A16.3, "What never happens").

THE EMAIL A16.3 ASKS FOR

`notify_order_limit` writes one in-app notice per account per billing period when the count
reaches 100 per cent. Since 10 October 2026 `notice_email` emails that notice through Resend
unless the seller has switched email off, once migration 0031 is applied. The note of
9 October saying the email waited on a provider is replaced by this one.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from .plans import PLAN_ORDER, PLANS

logger = logging.getLogger("myshopedge.order_usage")

LONDON = ZoneInfo("Europe/London")
LIVE = ("trialing", "active", "past_due")   # the same set as billing.LIVE
APPROACHING_PERCENT = 80

ORDER_USAGE_SQL = """
select q.plan_slug, q.status, q.current_period_start, q.current_period_end,
       q.orders_in_period
  from order_quota q
 where q.account_id = %(account)s
"""


class LargerPlan(BaseModel):
    slug: Literal["starter", "growth", "pro"]
    name: str
    order_limit: int


class OrderUsage(BaseModel):
    state: Literal["below", "approaching", "passed"]
    order_count: int
    order_limit: int
    plan: Literal["starter", "growth", "pro"]
    plan_name: str
    period_start: datetime
    period_end: datetime
    larger_plan: LargerPlan | None = None


def usage_state(count: int, limit: int) -> str:
    """`below`, `approaching` from 80 per cent, `passed` from 100 per cent."""
    if count >= limit:
        return "passed"
    if count * 100 >= limit * APPROACHING_PERCENT:
        return "approaching"
    return "below"


def larger_plan(slug: str) -> LargerPlan | None:
    """The next plan up in `PLAN_ORDER`, or None on the largest."""
    i = PLAN_ORDER.index(slug)
    if i + 1 >= len(PLAN_ORDER):
        return None
    p = PLANS[PLAN_ORDER[i + 1]]
    return LargerPlan(slug=p.slug, name=p.name, order_limit=p.order_limit)


def read_order_usage(conn, account_id: UUID | str, now: datetime) -> OrderUsage | None:
    """The account's usage in its current billing period, or None. Inside `tenant()`."""
    cur = conn.execute(ORDER_USAGE_SQL, {"account": str(account_id)})
    cols = [d.name for d in cur.description]
    row = cur.fetchone()
    if row is None:
        return None
    r: dict[str, Any] = dict(zip(cols, row, strict=True))
    start, end = r["current_period_start"], r["current_period_end"]
    if r["status"] not in LIVE or start is None or end is None or r["plan_slug"] not in PLANS:
        return None
    if not (start <= now < end):
        return None
    plan = PLANS[r["plan_slug"]]
    count = int(r["orders_in_period"])
    return OrderUsage(
        state=usage_state(count, plan.order_limit),
        order_count=count,
        order_limit=plan.order_limit,
        plan=plan.slug,
        plan_name=plan.name,
        period_start=start,
        period_end=end,
        larger_plan=larger_plan(plan.slug),
    )


def london_date(when: datetime) -> str:
    """'9 November 2026', the day in London."""
    d = when.astimezone(LONDON)
    return f"{d.day} {d.strftime('%B %Y')}"


def _orders(n: int) -> str:
    return f"{n:,} {'order' if n == 1 else 'orders'}"


def limit_notice(u: OrderUsage) -> tuple[str, str]:
    """The title and body of the notice at 100 per cent."""
    verb = "reached" if u.order_count == u.order_limit else "passed"
    title = f"This account has {verb} the {u.plan_name} plan's limit of {_orders(u.order_limit)}."
    body = (f"The shops on this account have taken {_orders(u.order_count)} in the billing "
            f"period that ends on "
            f"{london_date(u.period_end)}, and the {u.plan_name} plan covers "
            f"{_orders(u.order_limit)}. Cancelled orders count too. MyShopEdge keeps reading "
            "your orders, and your figures and exports carry on as before.")
    if u.larger_plan is not None:
        body += (f" The {u.larger_plan.name} plan covers up to "
                 f"{_orders(u.larger_plan.order_limit)} a month.")
    else:
        body += f" The {u.plan_name} plan is the largest MyShopEdge offers."
    return title, body


def notify_order_limit(conn, account_id: UUID | str, now: datetime) -> bool:
    """One notice per account per billing period, once the count reaches the limit.

    Inside `tenant()`. Called from `tiktok_sync.sync_shop`, which every read of a shop passes
    through: the daily run, the first read after a connection and a TikTok webhook. Today
    only reads, so it never writes this. The dedupe key names the account and the period's
    start, so a second sync in the same period writes nothing and the next period may write
    again. The period's start is written in UTC, so the key does not depend on the session's
    time zone. Returns whether a notice was written.

    A16.3 also asks for an email at 100 per cent. Nothing in this service can send one and no
    provider has been chosen, so the email is not sent; it waits on a provider.
    """
    u = read_order_usage(conn, account_id, now)
    if u is None or u.state != "passed":
        return False
    title, body = limit_notice(u)
    row = conn.execute(
        "insert into notifications (account_id, shop_id, type, severity, title, body, "
        "dedupe_key) values (%s, null, 'order_limit_passed', 'warning', %s, %s, %s) "
        "on conflict (account_id, dedupe_key) do nothing returning id",
        (str(account_id), title, body,
         f"order_limit_passed:{account_id}:{u.period_start.astimezone(timezone.utc).isoformat()}",
         )).fetchone()
    return row is not None
