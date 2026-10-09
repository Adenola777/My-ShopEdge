"""The two notices the alert settings promise (S27, STK-3). Built 9 October 2026.

`tiktok_sync.sync_shop` calls `raise_alert_notices` once its four domains have run, inside
the same `tenant()` transaction, so both notices are evaluated whenever a shop is read: by
the daily run, by the first read after a connection, and by a sync a TikTok webhook asks for.
Every write is idempotent, so evaluating twice in a day changes nothing.

STK-3 in the SRD reads: "Raise alerts for Out now, Low below the seller's threshold (default
14 days), and returns unchecked for 7 days." Its acceptance reads: "Each alert appears once
and clears when resolved." S27 adds that a change to a threshold "takes effect on the next
evaluation and does not re-raise notices already resolved".

LOW STOCK, `low_stock`

Which variants are low is read from `stock.positions`, the query behind S7 and the product
screen, so a notice can never call a variant low that the Stock screen does not. Low there
means `days_left` is below the shop's `alert_settings.low_stock_days` (14 when unset), and
`days_left` is null when nothing is on the shelf or nothing sold in fourteen days.

The notice is held to one per spell of low stock by its dedupe key, `low_stock:<sku id>`:

  * While the variant is low, the insert finds the key taken and writes nothing, whatever
    the seller has done with the notice. A notice the seller marked done is therefore not
    raised again while the variant stays low, including after a threshold change.
  * When the variant is next found healthy or with returns in transit, that is, no longer
    low and not out, the spell has ended. The notice is marked done, which is STK-3's
    "clears when resolved", and its key becomes `low_stock:<sku id>:cleared:<notice id>`,
    which frees `low_stock:<sku id>` for the next spell. A variant that recovers and then
    drops again is therefore told again, once.
  * A variant that goes from low to out keeps its spell open, because running out is not a
    recovery. **Not built:** STK-3's separate Out now alert. A variant that goes from
    healthy to out between two reads is never low in `stock.positions`, so it raises nothing
    here.

A threshold change acts on the next read through `stock.positions`, which reads the setting
afresh. Lowering it so a low variant is no longer low clears that variant's notice; raising
it so a healthy variant becomes low raises one. The one case in which a settings change can
lead to a second notice is a variant pushed out of low by one change and back in by another:
that is a new spell, and it is told as one. This reading of S27 is derived, not ruled.

Stock is evaluated only when this read's `inventory` domain finished completed or partial,
so a notice is never raised or cleared on a count this read failed to refresh.

RETURN CHECK REMINDER, `return_unchecked`

**Which items are still unchecked** is settled by the schema and the code:
`return_items.seller_check_status = 'pending'`. It is the status `sync_returns` gives an item
of a return with goods coming back, the status `checkReturnItem` accepts and leaves, and the
one S8 and Today count as awaiting a check. Cancellations and refunds with no goods back are
written `not_applicable`, so they never raise this notice (RET-9, TC-RET-13).

**When an item began waiting** is not settled by the facts, and the choice is derived:

  * `return_items.created_at` is when MyShopEdge wrote the item as pending, which is when it
    entered the seller's Check returns list. `sync_returns` writes items once, with the
    return, so the column is the first read of that return. This is the clock used here.
  * `returns.requested_at` is TikTok's `create_time`, when the buyer opened the return. It
    was not used, because the first read of a shop brings up to two years of returns, and a
    clock started by the buyer would remind the seller at once about returns MyShopEdge had
    never shown them.
  * Neither column records when the parcel reached the seller, and nothing in the repository
    names a TikTok field that does. The window therefore includes the days the goods spend in
    the post. The column's name, `coming_back_days`, suggests that is intended.

One notice is raised per return, keyed `return_unchecked:<return id>`, once its oldest pending
item has waited longer than `alert_settings.coming_back_days` (7 when unset), measured to the
end of the window this read covered (`until`, which the daily run sets to now). It clears,
by being marked done, once no item of the return is pending. A check is one way, so the
condition never comes back and the key is never freed. A threshold change decides when a
reminder is raised; a reminder already raised stays until the items are checked.

**Unverified.** `returns.status` holds TikTok's own return status, and no document in the
repository says which values mean the buyer withdrew the return or TikTok closed it. An item
of such a return stays pending in MyShopEdge, so it is listed in Check returns and is
reminded about here.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .dates import LONDON

log = logging.getLogger(__name__)

DEFAULT_COMING_BACK_DAYS = 7


def _days(value: float) -> str:
    """5.6 as "5.6 days", 6.0 as "6 days" and 1.0 as "1 day"."""
    text = f"{value:g}"
    return f"{text} {'day' if text == '1' else 'days'}"


def _units(n: int) -> str:
    return f"{n} {'unit' if n == 1 else 'units'}"


def _variant_name(title: str | None, variant: str | None, seller_sku: str | None) -> str:
    name = title or "A product TikTok did not name"
    if variant:
        name += f", {variant}"
    if seller_sku:
        name += f" (SKU {seller_sku})"
    return name


def low_stock_notices(conn, shop_id: str, account_id: str) -> dict[str, int]:
    """Raise one notice per spell of low stock, and clear the notice of a variant that has
    recovered. Returns how many were raised and cleared."""
    from .stock import DEFAULT_LOW_STOCK_DAYS, positions

    threshold = conn.execute(
        "select coalesce((select low_stock_days from alert_settings where shop_id = %s), %s)",
        (shop_id, DEFAULT_LOW_STOCK_DAYS)).fetchone()[0]
    names = {str(r[0]): r[1:] for r in conn.execute(
        "select k.id, p.title, k.variant_label, k.seller_sku from skus k "
        "left join products p on p.id = k.product_id where k.shop_id = %s", (shop_id,)).fetchall()}
    raised = cleared = 0
    for p in positions(conn, shop_id):
        sku = str(p.sku_id)
        key = f"low_stock:{sku}"
        if p.state == "low":
            title, variant, seller_sku = names.get(sku, (p.product_title, None, p.seller_sku))
            name = _variant_name(title, variant, seller_sku)
            row = conn.execute(
                "insert into notifications (account_id, shop_id, type, severity, title, body, "
                "entity_type, entity_id, dedupe_key) values (%s, %s, 'low_stock', 'warning', "
                "%s, %s, 'sku', %s, %s) on conflict (account_id, dedupe_key) do nothing returning id",
                (account_id, shop_id, f"{name} is low on stock.",
                 f"You have {_units(p.on_shelf)} on hand, which is {_days(p.days_left)} of cover "
                 f"at the rate of the last fourteen days. Your low stock threshold is "
                 f"{_days(threshold)}. Order more if you want to keep selling it, or change "
                 "the threshold in Alerts.",
                 sku, key)).fetchone()
            raised += row is not None
        elif p.state in ("healthy", "coming_back"):
            cur = conn.execute(
                "update notifications set status = 'done', "
                "dedupe_key = dedupe_key || ':cleared:' || id::text "
                "where account_id = %s and dedupe_key = %s", (account_id, key))
            cleared += cur.rowcount
    return {"raised": raised, "cleared": cleared}


RETURNS_DUE_SQL = """
select r.id::text, o.tiktok_order_id, min(ri.created_at) as waiting_since, count(*) as waiting,
       string_agg(coalesce(p.title, 'A product TikTok did not name')
                  || coalesce(', ' || k.variant_label, ''), '; ' order by ri.created_at, ri.id) as items
  from returns r
  join orders o on o.id = r.order_id
  join return_items ri on ri.return_id = r.id and ri.seller_check_status = 'pending'
  left join skus k on k.id = ri.sku_id
  left join products p on p.id = k.product_id
 where r.shop_id = %(shop)s
 group by r.id, o.tiktok_order_id
having min(ri.created_at) < %(until)s::timestamptz - make_interval(days => %(days)s)
"""


def return_check_notices(conn, shop_id: str, account_id: str, until: datetime) -> dict[str, int]:
    """Remind the seller once about each return whose items have waited longer than the
    shop's window, and clear the reminder once nothing in the return waits."""
    days = conn.execute(
        "select coalesce((select coming_back_days from alert_settings where shop_id = %s), %s)",
        (shop_id, DEFAULT_COMING_BACK_DAYS)).fetchone()[0]
    raised = 0
    for return_id, order, since, waiting, items in conn.execute(
            RETURNS_DUE_SQL, {"shop": shop_id, "until": until, "days": days}).fetchall():
        when = since.astimezone(LONDON).date()
        held, them, which = (("1 item", "the item reaches", "it") if waiting == 1
                             else (f"{waiting} items", "the items reach", "each item"))
        row = conn.execute(
            "insert into notifications (account_id, shop_id, type, severity, title, body, "
            "entity_type, entity_id, dedupe_key) values (%s, %s, 'return_unchecked', 'warning', "
            "%s, %s, 'return', %s, %s) on conflict (account_id, dedupe_key) do nothing returning id",
            (account_id, shop_id,
             f"The return on order {order} has waited more than {_days(days)} for your check.",
             f"MyShopEdge first read this return from TikTok on {when.day} {when:%B %Y}, and "
             f"it holds {held} still waiting for your check: {items}. When {them} you, open "
             f"Check returns and say whether {which} can be sold again.",
             return_id, f"return_unchecked:{return_id}")).fetchone()
        raised += row is not None
    cleared = conn.execute(
        "update notifications n set status = 'done' "
        "where n.account_id = %s and n.shop_id = %s and n.type = 'return_unchecked' "
        "and n.status <> 'done' and not exists (select 1 from return_items ri "
        "where ri.return_id = n.entity_id and ri.seller_check_status = 'pending')",
        (account_id, shop_id)).rowcount
    return {"raised": raised, "cleared": cleared}


def raise_alert_notices(conn, shop_id: str, until: datetime, outcome: dict[str, str]) -> dict[str, Any]:
    """Both evaluations, each in its own savepoint, so a fault in one leaves the other and the
    read itself untouched. A fault is logged and returned, never raised."""
    account_id = str(conn.execute("select account_id from shops where id = %s",
                                  (shop_id,)).fetchone()[0])
    result: dict[str, Any] = {}
    steps = [("return_unchecked", lambda: return_check_notices(conn, shop_id, account_id, until))]
    if outcome.get("inventory") in ("completed", "partial"):
        steps.insert(0, ("low_stock", lambda: low_stock_notices(conn, shop_id, account_id)))
    else:
        result["low_stock"] = "skipped: stock was not read"
    for name, step in steps:
        try:
            with conn.transaction():
                result[name] = step()
        except Exception as err:  # noqa: BLE001  a notice must never fail the read
            log.exception("%s notices for shop %s were not evaluated", name, shop_id)
            result[name] = f"error: {type(err).__name__}: {err}"
    return result
