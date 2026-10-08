"""Calls every route, because until 23 September 2026 nothing ever had.

Eight routes were served and none had been invoked. `test_contract_conformance.py` imports
the application and reads the schema FastAPI derives from the handlers, which exercises
their declarations and never their bodies. Every "verified against the seeded seller" line
in the service referred to SQL run by hand, not to the handler wrapping it.

That gap is how the authentication defect survived: the parts that were checked were
checked carefully, and the parts nobody called were assumed to work.

    python3 tests/test_handlers_smoke.py

It runs without a database, without credentials and without the network, by overriding the
account dependency and substituting a connection that returns canned rows.

**What this proves and what it does not.** It proves each handler executes end to end, that
its response validates against its own model, and that the arithmetic it performs on the
rows it is given is the arithmetic intended. It does not prove the SQL is right, because
the SQL never runs. A wrong query returning plausible rows would pass here and fail in
production, so this sits alongside the checks against the real database rather than
replacing them.
"""

import os, sys, hashlib, base64
from datetime import datetime, timezone, date
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NEON_AUTH_JWKS_URL", "http://127.0.0.1:1/jwks.json")
os.environ.setdefault("NEON_AUTH_AUDIENCE", "test")
os.environ.setdefault("NEON_AUTH_ISSUER", "https://test.invalid")

from fastapi.testclient import TestClient

from app.main import app
from app.auth import Account, require_account, require_signed_in
from app import discrepancies, products, records, settlements, shops, stock

ACCOUNT = Account(
    id=UUID("56e487ea-e0fa-3691-7857-724855e716fc"),
    email="owner@synthetic-uk-shop.test", name="Synthetic UK Shop Ltd",
    subject="user_synthetic_uk_shop",
)
SHOP = UUID("8a773a13-73b5-a382-7dd0-fda02e950369")
PRODUCT = UUID("11111111-1111-4111-8111-111111111111")
SKU = UUID("22222222-2222-4222-8222-222222222222")
NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


class Col:
    def __init__(self, name): self.name = name


class Result:
    """One canned answer. Chosen by matching text in the SQL, which is crude and honest.

    Matching on SQL text means a rewritten query silently falls through to an empty
    result rather than failing loudly. The KeyError below is what stops that being silent.
    """
    def __init__(self, cols, rows):
        self.description = [Col(c) for c in cols]
        self._rows = rows
    def fetchall(self): return self._rows
    def fetchone(self): return self._rows[0] if self._rows else None


class Conn:
    def __init__(self, answers): self.answers = answers
    def execute(self, sql, args=None):
        for needle, result in self.answers:
            if needle in " ".join(sql.split()):
                return result
        raise KeyError(f"No canned answer for: {' '.join(sql.split())[:140]}")
    def __enter__(self): return self
    def __exit__(self, *a): return False


failures = []

def check(name, fn):
    try:
        fn()
        print(f"  PASS  {name}")
    except Exception as exc:
        failures.append((name, exc))
        print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")


app.dependency_overrides[require_account] = lambda: ACCOUNT
app.dependency_overrides[require_signed_in] = lambda: ACCOUNT
app.dependency_overrides[shops.require_shop] = lambda: SHOP
client = TestClient(app)


def with_conn(module, answers):
    """Replace the module's tenant() for one call."""
    import contextlib
    @contextlib.contextmanager
    def fake(_account_id):
        yield Conn(answers)
    return fake


def _assert(cond, msg="assertion failed"):
    if not cond: raise AssertionError(msg)


print("handler smoke")

check("GET /health returns 200", lambda: _assert(client.get("/health").status_code == 200))


# --- billing plans needs no database at all
def plans():
    r = client.get("/v1/billing/plans")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:200]}")
    body = r.json()
    _assert(len(body["plans"]) == 3, f"expected 3 plans, got {len(body['plans'])}")
    _assert([p["slug"] for p in body["plans"]] == ["starter", "growth", "pro"])
check("GET /v1/billing/plans lists three plans in order", plans)


# --- a request the service cannot read answers as a problem whose detail is a sentence
# (8 October 2026: FastAPI's own answer put an array in detail, which forms render as text)
def validation_is_a_sentence():
    r = client.post("/v1/billing/subscription", json={"plan": "gold"})
    b = r.json()
    _assert(r.status_code == 422 and b["code"] == "validation_failed", r.text)
    _assert(isinstance(b["detail"], str) and b["detail"] == "Plan must be one of the choices offered.", b)
    _assert(b["title"] == "Some details need checking." and b["type"].endswith("/validation_failed"), b)
    r = client.post("/v1/billing/subscription", json={})
    _assert(r.status_code == 422 and r.json()["detail"] == "Plan is needed.", r.text)
check("an unreadable request gets a problem with a sentence, not an array", validation_is_a_sentence)


# --- titles are for people; the code stays in code and type
def titles_are_words():
    from app.problems import problem_response, TITLES
    import json as _json
    body = _json.loads(problem_response(409, "subscription_exists", "x").body)
    _assert(body["title"] == TITLES[409] and body["code"] == "subscription_exists", body)
check("a problem's title is words, and its code stays in code", titles_are_words)


# --- settlements list
def settlements_list():
    cols = ["id","tiktok_statement_id","tiktok_payment_id","settlement_reference",
            "statement_time","activity_date","paid_at","payment_status","currency",
            "statement_amount_minor","payable_amount_minor","total_reserve_amount_minor",
            "tiktok_invoice_number"]
    row = (UUID("33333333-3333-4333-8333-333333333333"), "202608A-0002", None, None,
           NOW, date(2026,8,15), None, "PAID", "GBP", 14750, 13750, -1000, None)
    settlements.tenant = with_conn(settlements, [("from settlements where", Result(cols, [row]))])
    r = client.get(f"/v1/shops/{SHOP}/settlements")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()["settlements"][0]
    _assert(b["statement_amount"]["amount_minor"] == 14750)
    _assert(b["total_reserve"]["amount_minor"] == -1000, "reserve must keep its sign")
    _assert(b["payable_amount"]["amount_minor"] == 13750)
check("GET settlements returns statement, reserve and payout as three figures", settlements_list)


# --- records
def records_page():
    cols = ["id","entry_type","category","tiktok_fee_type","amount_minor","currency",
            "occurred_at","basis_day","basis_month","source","source_ref","attribution",
            "order_id","tiktok_order_id","sku_id","tiktok_invoice_number",
            "reverses_entry_id","reason"]
    row = (UUID("44444444-4444-4444-8444-444444444444"), "sale", "gross_sales", None,
           36000, "GBP", NOW, date(2026,8,15), date(2026,8,1), "tiktok", None, "direct",
           None, None, SKU, None, None, None)
    records.tenant = with_conn(records, [
        ("coalesce(sum(le.amount_minor), 0)", Result(["s","c"], [(50038, "GBP")])),
        ("from ledger_entries le", Result(cols, [row])),
    ])
    r = client.get(f"/v1/shops/{SHOP}/records")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    _assert(b["total"]["amount_minor"] == 50038, "total is every page")
    _assert(b["shown_total"]["amount_minor"] == 36000, "shown_total is this page")
    _assert(b["entries"][0]["label"] == "Gross sales (GMV)", "A18.5: every category has words")
check("GET records distinguishes the total from the page sum", records_page)


# --- products ranking, and the arithmetic that matters
def products_ranking():
    cols = ["product_id","tiktok_product_id","title","units_sold","returns_units",
            "gross_sales_minor","net_proceeds_minor","currency","return_loss_minor",
            "cost_retained_minor","skus_without_cost","kept_minor"]
    desk = (PRODUCT, "P-DESK", "Computer Desk 120cm", 3, 1, 36000, 21300, "GBP",
            5100, 10200, 0, 6000)
    nocost = (UUID("55555555-5555-4555-8555-555555555555"), "P-X", "No cost yet",
              2, 0, 4000, 3000, "GBP", 0, None, 1, None)
    loose = Result(["category","tiktok_fee_type","amount_minor","currency"],
                   [("platform_adjustment", "PLATFORM_PENALTY", -500, "GBP")])
    products.tenant = with_conn(products, [
        ("and le.sku_id is null", loose),
        ("with scoped as", Result(cols, [desk, nocost])),
    ])
    r = client.get(f"/v1/shops/{SHOP}/products")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    rows = {p["title"]: p for p in b["products"]}
    _assert(rows["Computer Desk 120cm"]["kept"]["amount_minor"] == 6000)
    _assert(rows["Computer Desk 120cm"]["cost_known"] is True)
    # The product with no cost must report null rather than a figure that reads as profit.
    _assert(rows["No cost yet"]["kept"] is None, "kept must be null when a cost is missing")
    _assert(rows["No cost yet"]["cost_known"] is False)
    _assert(rows["No cost yet"]["kept_reason"] is not None, "a null kept must say why")
    # A product with an unknown cost ranks last rather than first.
    _assert(b["products"][0]["title"] == "Computer Desk 120cm")
    # Money that belongs to no product is its own line, named as the money screen names it.
    _assert(b["unattributed"]["amount"]["amount_minor"] == -500, b.get("unattributed"))
    _assert(b["unattributed"]["lines"][0]["label"] == "PLATFORM_PENALTY", b["unattributed"])
    # A product with no cost means the shop's profit is not known, so no shop total.
    _assert(b["shop_total"] is None, "no shop total while a cost is missing")
check("GET products returns null kept with a reason, and ranks unknowns last", products_ranking)


def products_shop_total():
    cols = ["product_id","tiktok_product_id","title","units_sold","returns_units",
            "gross_sales_minor","net_proceeds_minor","currency","return_loss_minor",
            "cost_retained_minor","skus_without_cost","kept_minor"]
    desk = (PRODUCT, "P-DESK", "Computer Desk 120cm", 3, 1, 36000, 21300, "GBP",
            5100, 10200, 0, 6000)
    loose = Result(["category","tiktok_fee_type","amount_minor","currency"],
                   [("platform_adjustment", "PLATFORM_PENALTY", -500, "GBP")])
    products.tenant = with_conn(products, [
        ("and le.sku_id is null", loose),
        ("with scoped as", Result(cols, [desk])),
    ])
    b = client.get(f"/v1/shops/{SHOP}/products").json()
    _assert(b["total"]["amount_minor"] == 6000, "total stays the products' own sum")
    _assert(b["shop_total"]["amount_minor"] == 5500, "shop total adds the unattributed line")
    products.tenant = with_conn(products, [
        ("and le.sku_id is null", Result(["category","tiktok_fee_type","amount_minor","currency"], [])),
        ("with scoped as", Result(cols, [desk])),
    ])
    b = client.get(f"/v1/shops/{SHOP}/products").json()
    _assert(b["unattributed"] is None and b["shop_total"]["amount_minor"] == 6000, b)
    # The kept ranking reaches down to return costs; gross sales asks for gross sales only.
    _assert("stock_written_off" in products._measure_categories("kept"))
    _assert("platform_adjustment" in products._measure_categories("net_proceeds"))
    _assert("stock_written_off" not in products._measure_categories("net_proceeds"))
    _assert(products._measure_categories("gross_sales") == ["gross_sales"])
check("GET products adds money tied to no product so the shop total meets Money", products_shop_total)


# --- money, the calculator for the whole shop
from app import money_view

MONEY_LINE_COLS = ["category","tiktok_fee_type","amount_minor","entries","unsettled","currency"]
MONEY_LINES = [
    ("gross_sales", None, 86200, 24, 2, "GBP"),
    ("seller_discount", None, -500, 2, 0, "GBP"),
    ("platform_commission", None, -5142, 24, 0, "GBP"),
    ("transaction_fee", None, -1283, 24, 0, "GBP"),
    ("unmapped_fee", "SOME_NEW_FEE", -199, 1, 0, "GBP"),
    ("platform_adjustment", "LOGISTICS_REIMBURSEMENT", -500, 1, 0, "GBP"),
    ("refund", None, -27400, 7, 0, "GBP"),
    ("return_shipping", None, -450, 1, 0, "GBP"),
    ("stock_written_off", None, -5100, 1, 0, "GBP"),
    ("reserve_withheld", "reserve_amount", -1000, 1, 0, "GBP"),
    ("settlement", None, -45388, 3, 0, "GBP"),
]
PRODUCT_COLS = ["product_id","tiktok_product_id","title","units_sold","returns_units",
                "gross_sales_minor","net_proceeds_minor","currency","return_loss_minor",
                "cost_retained_minor","skus_without_cost","kept_minor"]
DESK = (PRODUCT, "P-DESK", "Computer Desk 120cm", 3, 1, 36000, 21300, "GBP",
        5100, 10200, 0, 6000)
NOCOST = (UUID("55555555-5555-4555-8555-555555555555"), "P-X", "No cost yet",
          2, 0, 4000, 3000, "GBP", 0, None, 1, None)


def _money(products_rows):
    money_view.tenant = with_conn(money_view, [
        ("count(*) filter (where le.settlement_id is null", Result(MONEY_LINE_COLS, MONEY_LINES)),
        ("with scoped as", Result(PRODUCT_COLS, products_rows)),
    ])


def money_chain():
    _money([DESK])
    r = client.get(f"/v1/shops/{SHOP}/money")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    keys = [s["key"] for s in b["sections"]]
    _assert(keys == ["revenue","tiktok_fees","refunds","your_costs","return_costs","payout"],
            f"A8.5 order, then the payout section last: {keys}")
    sec = {s["key"]: s for s in b["sections"]}
    _assert(sec["revenue"]["subtotal"]["amount_minor"] == 85700)
    _assert(sec["revenue"]["subtotal_label"] == "Net sales")
    fees = sec["tiktok_fees"]
    labels = [l["label"] for l in fees["lines"]]
    # The adjustment sits inside TikTok fees under TikTok's own name, as ruled.
    _assert("LOGISTICS_REIMBURSEMENT" in labels, f"adjustment inside fees: {labels}")
    _assert("SOME_NEW_FEE" in labels, "an unrecognised fee keeps TikTok's name")
    _assert(fees["subtotal"]["amount_minor"] == 78576)
    _assert(sec["refunds"]["subtotal"]["amount_minor"] == 51176)
    _assert(sec["refunds"]["subtotal_label"] == "Net proceeds")
    # Cost of goods is computed from retained cost, never read from the ledger (A4.1).
    cogs = sec["your_costs"]["lines"][0]
    _assert(cogs["category"] == "cost_of_goods_sold" and cogs["amount"]["amount_minor"] == -10200)
    _assert(sec["your_costs"]["subtotal"]["amount_minor"] == 40976)
    _assert(sec["return_costs"]["subtotal"]["amount_minor"] == 35426)
    _assert(sec["return_costs"]["subtotal_label"] == "Gross profit after returns")
    t = b["totals"]
    _assert(t["gross_sales"]["amount_minor"] == 86200)
    _assert(t["net_sales"]["amount_minor"] == 85700)
    _assert(t["net_proceeds"]["amount_minor"] == 51176)
    _assert(t["cost_of_goods_sold"]["amount_minor"] == -10200)
    _assert(t["gross_profit"]["amount_minor"] == 40976)
    _assert(t["gross_profit_after_returns"]["amount_minor"] == 35426)
    _assert(b["kept"]["amount_minor"] == 35426 and b["kept_reason"] is None)
    # Reserve and payout keep the ledger's signs and are not part of the chain.
    payout = sec["payout"]
    _assert([l["label"] for l in payout["lines"]] == ["Reserve withheld", "Payout"])
    _assert(payout["subtotal"]["amount_minor"] == -46388)
    _assert(b["cost_coverage"] == 1.0)
    _assert(b["unmapped_fee_count"] == 1)
    _assert(b["period"]["basis"] == "sales" and b["granularity"] == "month")
    # Two sales have no settlement yet, so the sales basis is an estimate.
    _assert(b["confidence"] == "estimated", b["confidence"])
check("GET money follows A8.5 and puts the adjustment inside TikTok fees", money_chain)


def money_cash_is_confirmed():
    _money([DESK])
    r = client.get(f"/v1/shops/{SHOP}/money?basis=cash")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    _assert(r.json()["confidence"] == "confirmed", r.json()["confidence"])
check("GET money on the cash basis is confirmed", money_cash_is_confirmed)


def money_incomplete_costs():
    _money([DESK, NOCOST])
    r = client.get(f"/v1/shops/{SHOP}/money")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    _assert(b["cost_coverage"] == 0.5, b["cost_coverage"])
    _assert(b["confidence"] == "incomplete")
    _assert(b["kept"] is None and b["kept_reason"] == "incomplete_costs")
    t = b["totals"]
    _assert(t["gross_profit"] is None and t["gross_profit_after_returns"] is None,
            "gross profit is null, never a figure that leaves the goods out")
    _assert("cost_of_goods_sold" not in t, "an unknown cost is omitted, not sent as zero")
    _assert(t["net_proceeds"]["amount_minor"] == 51176, "net proceeds needs no cost")
    sec = {s["key"]: s for s in b["sections"]}
    _assert("your_costs" not in sec, "no cost line and no postage means no section")
    _assert(sec["return_costs"]["subtotal"]["amount_minor"] == -5550)
    _assert(sec["return_costs"]["subtotal_label"] == "Total return costs")
check("GET money with a missing cost returns null gross profit and says why", money_incomplete_costs)


def money_etag():
    _money([DESK])
    first = client.get(f"/v1/shops/{SHOP}/money")
    tag = first.headers.get("etag")
    _assert(tag, "an ETag is sent")
    _money([DESK])
    again = client.get(f"/v1/shops/{SHOP}/money", headers={"If-None-Match": tag})
    _assert(again.status_code == 304, f"status {again.status_code}")
check("GET money answers 304 when nothing has changed", money_etag)


# --- today, which reuses the calculator and counts what needs the seller
from datetime import timedelta
from app import today_view

SHOP_MONEY_COLS = ["status","amount_minor","postage_minor","orders","currency"]
# The development ledger's own figures. Settled includes the 4.50 of return postage TikTok
# deducted, so it is 453.88, which is the payout TikTok made.
SHOP_MONEY_ROWS = [("delivered_awaiting_settlement", 1850, None, 1, "GBP"),
                   ("settled", 45388, -450, 18, "GBP"),
                   ("waiting_delivery", 1850, None, 1, "GBP")]
NEEDS_COLS = ["returns_to_check","open_discrepancies","out_of_stock","missing_costs",
              "unmapped_fees","unmapped_fee_minor","last_synced_at","connection_status",
              "access_expires_at","refresh_expires_at","revoked_at","connections",
              "refresh_failure_code","refresh_attempted_at","refresh_succeeded_at",
              "missing_scopes","latest_sync_statuses"]


def _needs(**over):
    base = dict(returns_to_check=0, open_discrepancies=1, out_of_stock=1, missing_costs=0,
                unmapped_fees=1, unmapped_fee_minor=199, last_synced_at=None,
                connection_status="connected", access_expires_at=None,
                refresh_expires_at=None, revoked_at=None, connections=1,
                refresh_failure_code=None, refresh_attempted_at=None,
                refresh_succeeded_at=None, missing_scopes=[], latest_sync_statuses=None)
    base.update(over)
    return Result(NEEDS_COLS, [tuple(base[c] for c in NEEDS_COLS)])


def _today(products_rows, needs):
    today_view.tenant = with_conn(today_view, [
        ("count(*) filter (where le.settlement_id is null", Result(MONEY_LINE_COLS, MONEY_LINES)),
        ("with scoped as", Result(PRODUCT_COLS, products_rows)),
        ("left join order_settlements os", Result(SHOP_MONEY_COLS, SHOP_MONEY_ROWS)),
        ("seller_check_status = 'pending'", needs),
    ])
    r = client.get(f"/v1/shops/{SHOP}/today")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    return r.json()


def today_complete():
    b = _today([DESK], _needs())
    _assert(b["hero"]["label"] == "gross_profit_after_returns", b["hero"]["label"])
    _assert(b["hero"]["value"]["amount_minor"] == 35426)
    _assert(b["hero"]["confidence"] == "estimated")
    _assert(b["month"]["gross"]["amount_minor"] == 86200)
    _assert(b["month"]["kept"]["amount_minor"] == 35426)
    sm = b["shop_money"]
    # A29.7: generated is net proceeds, paid out is what TikTok paid, and the return postage
    # TikTok deducted is stated rather than dropped, so the three reconcile.
    _assert(sm["generated"]["amount_minor"] == 49538)
    _assert(sm["paid_out"]["amount_minor"] == 45388, "paid out equals the real payout")
    _assert(sm["awaiting"]["amount_minor"] == 3700)
    _assert(sm["return_postage"]["amount_minor"] == -450)
    _assert(sm["paid_out"]["amount_minor"] + sm["awaiting"]["amount_minor"]
            == sm["generated"]["amount_minor"] + sm["return_postage"]["amount_minor"])
    _assert(b["freshness"] == {"status": "stale", "last_synced_at": None})
    _assert([a["status"] for a in sm["awaiting_breakdown"]]
            == ["delivered_awaiting_settlement", "waiting_delivery"])
    # Never synced means stale, and the list runs warning before info, money first.
    _assert(b["stale"] is True)
    types = [(i["type"], i["severity"]) for i in b["needs_you"]]
    _assert(types == [("unmapped_fees", "warning"), ("open_discrepancies", "warning"),
                      ("first_sync_pending", "info"), ("out_of_stock", "info")], types)
    _assert(b["needs_you"][0]["amount_at_stake"]["amount_minor"] == 199)
check("GET today leads with gross profit after returns and reconciles Shop Money", today_complete)


def today_incomplete():
    b = _today([DESK, NOCOST], _needs(missing_costs=1))
    _assert(b["hero"]["label"] == "net_proceeds", "A8 withdrew Left after TikTok")
    _assert(b["hero"]["value"]["amount_minor"] == 51176)
    _assert(b["hero"]["confidence"] == "incomplete")
    _assert(b["month"]["kept"] is None and b["month"]["kept_reason"] == "incomplete_costs")
    _assert(any(i["type"] == "missing_costs" and i["severity"] == "info" for i in b["needs_you"]))
check("GET today falls back to net proceeds when a cost is missing", today_incomplete)


def today_connection():
    now = datetime.now(timezone.utc)
    b = _today([DESK], _needs(last_synced_at=now - timedelta(hours=2),
                               refresh_expires_at=now + timedelta(days=10),
                               access_expires_at=now + timedelta(days=3)))
    _assert(b["stale"] is False, "synced two hours ago is not stale")
    warn = [i["type"] for i in b["needs_you"] if i["severity"] == "warning"]
    # Within a severity, the item with money at stake leads, then the others by count.
    _assert(warn == ["unmapped_fees", "connection_expiring", "open_discrepancies"], warn)
    b = _today([DESK], _needs(last_synced_at=now - timedelta(hours=30), revoked_at=now))
    _assert(b["stale"] is True)
    _assert(b["needs_you"][0]["type"] == "connection_action_required")
    _assert(b["needs_you"][0]["severity"] == "critical")
    _assert(any(i["type"] == "stale_data" for i in b["needs_you"]))
check("GET today puts a broken connection first and flags a stale sync", today_connection)


def today_freshness():
    now = datetime.now(timezone.utc)
    for hours, expected in ((1, "fresh"), (5.9, "fresh"), (6, "getting_old"),
                            (23.9, "getting_old"), (24.1, "stale")):
        b = _today([DESK], _needs(last_synced_at=now - timedelta(hours=hours)))
        _assert(b["freshness"]["status"] == expected, f"{hours}h gave {b['freshness']['status']}")
        _assert(b["stale"] == (expected == "stale"), f"{hours}h stale={b['stale']}")
check("GET today reports fresh, getting old and stale at the ruled boundaries", today_freshness)


def today_health():
    now = datetime.now(timezone.utc)
    b = _today([DESK], _needs(
        last_synced_at=now - timedelta(hours=1),
        refresh_failure_code="36004004", refresh_attempted_at=now,
        refresh_succeeded_at=now - timedelta(days=2),
        missing_scopes=["seller.return.info"],
        latest_sync_statuses=["completed", "failed", "partial"]))
    by = {i["type"]: i["severity"] for i in b["needs_you"]}
    _assert(by.get("refresh_failed") == "critical", by)
    _assert(by.get("missing_scope") == "critical", by)
    _assert(by.get("sync_failed") == "warning" and by.get("sync_partial") == "warning", by)
    sev = [i["severity"] for i in b["needs_you"]]
    _assert(sev == sorted(sev, key=lambda x: {"critical": 0, "warning": 1, "info": 2}[x]),
            f"critical, then warning, then info: {sev}")
    # A refresh that has since succeeded is not a failure.
    b = _today([DESK], _needs(last_synced_at=now, refresh_failure_code="36004004",
                               refresh_attempted_at=now - timedelta(hours=2),
                               refresh_succeeded_at=now - timedelta(hours=1)))
    _assert(all(i["type"] != "refresh_failed" for i in b["needs_you"]))
check("GET today raises refresh, scope and sync failures at their ruled severities", today_health)


# --- the two connection handlers
#
# These matter more than the readers. The callback is the only unauthenticated endpoint in
# the service, and the state is the only thing standing between a seller's ledger and a
# shop they never approved. A handler that accepts any state connects the wrong shop.
import contextlib

from app import connections


def _fake_unscoped(answers):
    @contextlib.contextmanager
    def fake():
        yield Conn(answers)
    return fake


def connection_unconfigured():
    for var in ("TIKTOK_SERVICE_ID", "TIKTOK_APP_KEY", "TIKTOK_APP_SECRET"):
        os.environ.pop(var, None)
    r = client.post("/v1/connections/tiktok/authorize")
    _assert(r.status_code == 503, f"status {r.status_code}: {r.text[:200]}")
    _assert(r.json()["code"] == "tiktok_unconfigured", r.text[:200])
check("POST authorize refuses when TikTok is not configured", connection_unconfigured)


def authorize_rejects_open_redirect():
    os.environ["TIKTOK_SERVICE_ID"] = "7688277529379407633"
    connections.tenant = with_conn(connections, [("insert into tiktok_auth_state", Result([], []))])
    # A protocol-relative URL passes a naive "starts with /" check and sends the seller to
    # another host. That is the account takeover the contract warns about.
    for bad in ("//evil.example/x", "https://evil.example", "/ok\\evil"):
        r = client.post("/v1/connections/tiktok/authorize", json={"return_to": bad})
        _assert(r.status_code == 400, f"{bad!r} was accepted: {r.status_code}")
        _assert(r.json()["code"] == "return_to_not_allowed", r.text[:200])
check("POST authorize refuses an off-site return_to", authorize_rejects_open_redirect)


def authorize_issues_a_link():
    os.environ["TIKTOK_SERVICE_ID"] = "7688277529379407633"
    written = {}

    class Recorder(Conn):
        def execute(self, sql, args=None):
            if "insert into tiktok_auth_state" in " ".join(sql.split()):
                written["digest"], written["account"] = args[0], args[1]
                return Result([], [])
            return super().execute(sql, args)

    @contextlib.contextmanager
    def fake(_account_id):
        yield Recorder([])
    connections.tenant = fake

    r = client.post("/v1/connections/tiktok/authorize", json={"return_to": "/connect/done"})
    _assert(r.status_code == 201, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    # A23.1. The seller link, not the partner link. Using the partner host is what produced
    # an Indonesian sandbox shop three times on 23 September.
    _assert(b["authorization_url"].startswith("https://services.tiktokshop.com/open/authorize"),
            f"wrong authorisation host: {b['authorization_url']}")
    _assert("partner.tiktokshop.com" not in b["authorization_url"])
    _assert(f"state={b['state']}" in b["authorization_url"], "the link must carry the state")
    _assert(len(b["state"]) >= 32, "the state must be long enough not to be guessed")
    # The stored value is the digest. A readable copy of the table must be worthless.
    _assert(written["digest"] != b["state"], "the raw state must never be stored")
    _assert(written["digest"] == hashlib.sha256(b["state"].encode()).hexdigest())
    _assert(written["account"] == str(ACCOUNT.id), "the state is bound to this account")
check("POST authorize issues a seller link and stores only the digest", authorize_issues_a_link)


def callback_refuses_unknown_state():
    # consume_tiktok_auth_state returns no row for unknown, spent and expired alike.
    connections.unscoped = _fake_unscoped([("consume_tiktok_auth_state", Result(["a", "r"], []))])
    r = client.get("/v1/connections/tiktok/callback", params={"code": "c", "state": "whatever"})
    _assert(r.status_code == 400, f"status {r.status_code}: {r.text[:200]}")
    _assert(r.json()["code"] == "state_invalid", r.text[:200])
    # The detail must not echo what it was given back into a page the seller may screenshot.
    _assert("whatever" not in r.text and "c" != r.json()["detail"], "the detail echoed the input")
check("GET callback refuses a state it did not issue", callback_refuses_unknown_state)


def callback_refuses_a_creator_account():
    connections.unscoped = _fake_unscoped(
        [("consume_tiktok_auth_state", Result(["a", "r"], [(ACCOUNT.id, "/connect/done")]))]
    )
    # A23.3. user_type 1 is a creator. Anything but 0 means the wrong authorisation link.
    connections._exchange_code = lambda code: {"access_token": "t", "user_type": 1}
    r = client.get("/v1/connections/tiktok/callback", params={"code": "c", "state": "s"})
    _assert(r.status_code == 400, f"status {r.status_code}: {r.text[:200]}")
    _assert(r.json()["code"] == "not_a_seller_account", r.text[:200])
check("GET callback refuses a TikTok account that is not a seller", callback_refuses_a_creator_account)


def signature_follows_the_documented_steps():
    """TikTok's algorithm, checked against the four properties its page states.

    There is no worked example with an expected digest on TikTok's page, so this cannot
    assert a known-good value. It asserts the properties that distinguish the documented
    algorithm from the obvious wrong implementations of it, which is what a refactor would
    break. The first live call remains the real test.
    """
    sign, secret = connections._sign, "SECRET"
    base = sign("/authorization/202309/shops", {"app_key": "k", "timestamp": "1"}, b"", secret)

    # sign and access_token are excluded, so adding either changes nothing.
    _assert(base == sign("/authorization/202309/shops",
                         {"app_key": "k", "timestamp": "1", "sign": "x"}, b"", secret),
            "sign must be excluded from its own input")
    _assert(base == sign("/authorization/202309/shops",
                         {"app_key": "k", "timestamp": "1", "access_token": "t"}, b"", secret),
            "access_token must be excluded: it travels in a header and is not signed")

    # The path is part of the input, so the same parameters on another path differ.
    _assert(base != sign("/authorization/202403/shops",
                         {"app_key": "k", "timestamp": "1"}, b"", secret),
            "the request path must be part of the signed input")

    # The body is appended.
    _assert(base != sign("/authorization/202309/shops",
                         {"app_key": "k", "timestamp": "1"}, b"{}", secret),
            "the body must be part of the signed input")

    # Keys sort alphabetically, so a value moved between keys changes the concatenation.
    _assert(sign("/p", {"a": "1", "b": "2"}, b"", secret)
            != sign("/p", {"a": "12", "b": ""}, b"", secret),
            "keys and values must concatenate as {key}{value} in sorted order")

    # Hex SHA-256.
    _assert(len(base) == 64 and all(c in "0123456789abcdef" for c in base), base)
check("the signature follows TikTok's documented steps", signature_follows_the_documented_steps)


def tokens_round_trip_and_refuse_a_missing_key():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    os.environ.pop("TIKTOK_TOKEN_KEY", None)
    try:
        connections._encrypt("secret-token")
        raise AssertionError("a missing key must refuse rather than store in the clear")
    except Exception as exc:
        _assert(getattr(exc, "code", None) == "token_encryption_unconfigured", repr(exc))

    key = AESGCM.generate_key(bit_length=256)
    os.environ["TIKTOK_TOKEN_KEY"] = base64.b64encode(key).decode()
    blob = connections._encrypt("secret-token")
    _assert(b"secret-token" not in blob, "the token must not appear in the ciphertext")
    back = AESGCM(key).decrypt(blob[:12], blob[12:], None).decode()
    _assert(back == "secret-token", "the token must decrypt to what went in")
    # A fresh nonce every time, so the same token does not produce the same bytes.
    _assert(connections._encrypt("secret-token") != blob, "the nonce must not repeat")
check("tokens encrypt, round trip, and refuse to store without a key", tokens_round_trip_and_refuse_a_missing_key)


GB_SHOP = {"id": "7495", "code": "GBGBLCRKQTEX", "name": "My ShopEdge",
           "region": "GB", "seller_type": "LOCAL", "cipher": "GCP_test"}


def _callback_with(shop, written):
    connections.unscoped = _fake_unscoped(
        [("consume_tiktok_auth_state", Result(["a", "r"], [(ACCOUNT.id, "/connect/done")]))]
    )
    connections._exchange_code = lambda code: {
        "access_token": "act.tok", "refresh_token": "rft.tok", "user_type": 0,
        # The values the first real authorisation returned, 29 September 2026. Unix times.
        "access_token_expire_in": 1791309162, "refresh_token_expire_in": 4912765591,
        "granted_scopes": ["seller.finance"],
    }
    connections._authorized_shops = lambda token: shop if isinstance(shop, list) else [shop]

    class Writer(Conn):
        def execute(self, sql, args=None):
            flat = " ".join(sql.split())
            if "insert into shops" in flat:
                written["shop"] = args
                written.setdefault("shops", []).append(args)
                return Result(["id"], [(SHOP,)])
            if "insert into tiktok_connections" in flat:
                written["conn"] = args
                written.setdefault("conns", []).append(args)
                return Result([], [])
            return Result([], [])

    @contextlib.contextmanager
    def fake(_account_id):
        yield Writer([])
    connections.tenant = fake
    # The first read after connecting runs as a background task; recorded, not run.
    connections._first_sync = lambda shop_id, account_id: written.setdefault("first_sync", []).append(
        (str(shop_id), str(account_id)))
    return client.get("/v1/connections/tiktok/callback", params={"code": "c", "state": "s"})


def callback_connects_a_gb_shop():
    written = {}
    r = _callback_with(GB_SHOP, written)
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:400]}")
    b = r.json()
    _assert(b["accepted"] is True, b)
    _assert(b["rejection_reason"] is None, b)
    _assert(b["shop"]["tiktok_shop_code"] == "GBGBLCRKQTEX", b["shop"])
    _assert(b["shop"]["seller_type"] == "LOCAL", b["shop"])
    # The contract says the connection is recorded as pending, not connected.
    _assert(b["shop"]["connection_status"] == "pending", b["shop"])
    _assert(b["return_to"] == "/connect/done", b)
    # Nothing readable reaches the database.
    enc_access, enc_refresh, enc_cipher = written["conn"][1], written["conn"][2], written["conn"][3]
    _assert(b"act.tok" not in enc_access, "the access token was stored in the clear")
    _assert(b"rft.tok" not in enc_refresh, "the refresh token was stored in the clear")
    _assert(b"GCP_test" not in enc_cipher, "the shop cipher was stored in the clear")
    # TikTok's *_expire_in fields are Unix times. Read as durations, the access token
    # lasted until 2083 and was never refreshed.
    _assert(written["conn"][4] == datetime(2026, 10, 6, 17, 52, 42, tzinfo=timezone.utc), written["conn"][4])
    _assert(written["conn"][5] == datetime(2125, 9, 5, 17, 6, 31, tzinfo=timezone.utc), written["conn"][5])
    # The shop is read straight away, once (8 October 2026).
    _assert(written.get("first_sync") == [(str(SHOP), str(ACCOUNT.id))], written.get("first_sync"))
check("GET callback connects a GB shop and stores nothing readable", callback_connects_a_gb_shop)


def callback_lists_but_refuses_an_unsupported_shop():
    # A28: the shop is stored and listed, and it produces no figures. Refusing outright
    # would lose the authorisation the seller just granted.
    for field, value, reason in [("region", "ID", "region_unsupported"),
                                 ("seller_type", "CROSS_BORDER", "seller_type_unsupported")]:
        w = {}
        r = _callback_with({**GB_SHOP, field: value}, w)
        _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
        b = r.json()
        _assert(b["accepted"] is False, b)
        _assert(b["rejection_reason"] == reason, b)
        _assert(b["shop"] is not None, "the shop must still be listed")
        _assert(not w.get("first_sync"), "an unsupported shop must not be read")
check("GET callback stores an unsupported shop but marks it not accepted", callback_lists_but_refuses_an_unsupported_shop)


def callback_stores_every_authorised_shop():
    from app.tiktok_api import decrypt as _decrypt
    # A31.7: an account holds every shop its authorisation covers.
    ikonetu = {"id": "7494930319769175829", "code": "GBGBLCUKQTCE", "name": "IkonetU",
               "region": "GB", "seller_type": "LOCAL", "cipher": "GCP_other"}
    written = {}
    r = _callback_with([{**GB_SHOP, "region": "ID"}, ikonetu], written)
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    _assert([a[2] for a in written["shops"]] == ["GBGBLCRKQTEX", "GBGBLCUKQTCE"], written["shops"])
    _assert(len(written["conns"]) == 2, "each shop needs its own connection row")
    # Same tokens, each shop's own cipher.
    a, b = written["conns"]
    _assert(a[4] == b[4] and a[5] == b[5], "both shops carry the same expiry")
    _assert(_decrypt(a[3]) == "GCP_test" and _decrypt(b[3]) == "GCP_other")
    # The contract returns one shop: the first accepted one.
    _assert(r.json()["shop"]["tiktok_shop_code"] == "GBGBLCUKQTCE" and r.json()["accepted"] is True, r.json())
check("GET callback stores every shop TikTok authorises, each with its own cipher", callback_stores_every_authorised_shop)


# --- stock, movements and discrepancies
STOCK_COLS = ["sku_id","tiktok_sku_id","seller_sku","product_title","tiktok_stock",
              "adjusted_delta","on_shelf","sold_not_posted","coming_back","written_off",
              "as_of","days_left","state"]

def _stock_row(sku, on_shelf, days_left, state):
    from decimal import Decimal
    return (sku, "1729", "SKU", "Title", on_shelf, 0, on_shelf, 0, 0, 0, NOW,
            Decimal(days_left) if days_left is not None else None, state)

def stock_page():
    rows = [_stock_row(UUID(int=i), 5, "3.5", "low") for i in range(1, 4)]
    stock.tenant = with_conn(stock, [
        ("with settings as", Result(STOCK_COLS, rows)),
        ("select max(as_of) from stock_positions", Result(["m"], [(NOW,)])),
    ])
    r = client.get(f"/v1/shops/{SHOP}/stock?limit=2&state=low")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    _assert(len(b["items"]) == 2, "the extra row only signals another page")
    _assert(b["items"][0]["days_left"] == 3.5, b["items"][0])
    _assert(b["items"][0]["state"] == "low")
    _assert(b["next_cursor"] is not None)
    r2 = client.get(f"/v1/shops/{SHOP}/stock?cursor={b['next_cursor']}")
    _assert(r2.status_code == 200, f"status {r2.status_code}: {r2.text[:300]}")
check("GET stock pages by SKU and serves days left as a number", stock_page)

def stock_out_is_null():
    stock.tenant = with_conn(stock, [
        ("with settings as", Result(STOCK_COLS, [_stock_row(SKU, 0, None, "out")])),
        ("select max(as_of) from stock_positions", Result(["m"], [(NOW,)])),
    ])
    b = client.get(f"/v1/shops/{SHOP}/stock").json()
    _assert(b["items"][0]["days_left"] is None, "A12 row 29: sold out is null, not a division")
    _assert(b["next_cursor"] is None)
check("GET stock returns null days left for a sold out SKU", stock_out_is_null)

def stock_refuses_bad_input():
    _assert(client.get(f"/v1/shops/{SHOP}/stock?cursor=nonsense").status_code == 400)
    _assert(client.get(f"/v1/shops/{SHOP}/stock?state=gone").status_code == 422)
check("GET stock refuses a malformed cursor and an unknown state", stock_refuses_bad_input)

MOVE_COLS = ["id","movement_type","quantity","occurred_at","order_id","return_id",
             "reason","created_by"]

def movements_page():
    rows = [(UUID(int=i), "manual_adjustment", -2, NOW, None, None, "Damaged", None)
            for i in range(1, 3)]
    stock.tenant = with_conn(stock, [
        ("from skus k join products p", Result(
            ["id","product_id","title","variant_label","seller_sku","tiktok_sku_id"],
            [(SKU, PRODUCT, "Computer Desk 120cm", "Black", "DESK-BLK", "1729100000000000004")])),
        ("from stock_movements where", Result(MOVE_COLS, rows)),
    ])
    r = client.get(f"/v1/shops/{SHOP}/stock/{SKU}/movements?limit=1")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    _assert(b["movements"][0]["quantity"] == -2)
    _assert(b["movements"][0]["reason"] == "Damaged")
    _assert(b["next_cursor"] is not None)
    # The screen that adjusts this variant's stock must be able to say which item it is.
    _assert(b["sku"]["product_title"] == "Computer Desk 120cm" and b["sku"]["seller_sku"] == "DESK-BLK", b["sku"])
check("GET movements lists a SKU's ledger newest first", movements_page)

def movements_unknown_sku():
    stock.tenant = with_conn(stock, [("from skus k join products p", Result(["x"], []))])
    r = client.get(f"/v1/shops/{SHOP}/stock/{SKU}/movements")
    _assert(r.status_code == 404, f"status {r.status_code}")
    _assert(r.json()["code"] == "sku_not_found")
check("GET movements answers 404 for a SKU outside the shop", movements_unknown_sku)

DISC_COLS = ["id","kind","entity_type","entity_id","field","tiktok_value","seller_value",
             "applied_value","status","resolution","note","effect","opened_at","resolved_at"]

def discrepancies_page():
    row = (UUID(int=7), "unmapped_fee", "settlement", None, "adjustment_amount", "-5.00",
           None, "-5.00", "open", None, "PLATFORM_PENALTY", None, NOW, None)
    discrepancies.tenant = with_conn(discrepancies, [
        ("from discrepancies where shop_id = %s and status = 'open'", Result(["c"], [(2,)])),
        ("from discrepancies where", Result(DISC_COLS, [row])),
    ])
    r = client.get(f"/v1/shops/{SHOP}/discrepancies?kind=unmapped_fee")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    _assert(b["open_count"] == 2, "TC-DSC-05: the open count ignores the page filters")
    _assert(b["discrepancies"][0]["kind"] == "unmapped_fee")
    _assert(b["discrepancies"][0]["applied_value"] == "-5.00")
    _assert(b["discrepancies"][0]["correctable"] is False, "an unmapped fee is TikTok's fact")
check("GET discrepancies serves the seventh kind and an unfiltered open count", discrepancies_page)


def product_detail_stock_state():
    # getProduct had never been invoked. When it was, on 24 September, its stock state was
    # its own "in_stock" or "out_of_stock", outside the contract's enum. It now reads the
    # position from stock.positions, the one place the stock rule lives.
    rank_cols = ["product_id","tiktok_product_id","title","units_sold","returns_units",
                 "gross_sales_minor","net_proceeds_minor","currency","return_loss_minor",
                 "cost_retained_minor","skus_without_cost","kept_minor"]
    desk = (PRODUCT, "P-DESK", "Computer Desk 120cm", 3, 1, 36000, 21300, "GBP",
            5100, 10200, 0, 6000)
    products.tenant = with_conn(products, [
        ("from products where id=%s", Result(["id","tiktok_product_id","title"],
                                              [(PRODUCT, "P-DESK", "Computer Desk 120cm")])),
        ("group by le.category, le.tiktok_fee_type",
         Result(["category","tiktok_fee_type","amount_minor","currency"],
                [("gross_sales", None, 36000, "GBP")])),
        ("from skus s where s.product_id", Result(["id","tiktok_sku_id","seller_sku",
                                                   "variant_label","cost_minor"],
                                                  [(SKU, "1729", "DESK-BLK", None, 3400)])),
        ("with settings as", Result(STOCK_COLS, [_stock_row(SKU, 0, None, "out")])),
        ("with scoped as", Result(rank_cols, [desk])),
    ])
    r = client.get(f"/v1/shops/{SHOP}/products/{PRODUCT}")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    st = r.json()["stock"]
    _assert(st is not None and st["state"] == "out", st)
    _assert(st["days_left"] is None)
check("GET product detail takes its stock state from the one stock rule", product_detail_stock_state)


def needs_you_links_only_to_built_screens():
    from app.today_view import needs_href
    d = date(2026, 9, 24)
    _assert(needs_href("open_discrepancies", SHOP, d) == f"/shops/{SHOP}/discrepancies?status=open")
    _assert(needs_href("unmapped_fees", SHOP, d).endswith(
        "records?category=unmapped_fee&from=2026-09-01&to=2026-09-24"))
    _assert(needs_href("out_of_stock", SHOP, d) == f"/shops/{SHOP}/stock?state=out")
    # No screen yet, so no link rather than a link to nothing.
    _assert(needs_href("returns_to_check", SHOP, d) is None)
    _assert(needs_href("connection_action_required", SHOP, d) is None)
check("Needs you links only to screens that exist", needs_you_links_only_to_built_screens)


def product_and_money_use_the_same_words():
    # A8 and TC-CLR-06. The product calculator and the Money calculator name the same money,
    # so they must use the same words, and none of the withdrawn labels may appear.
    from app import money_view
    for key, label in products.LABELS.items():
        _assert(money_view.LABELS.get(key) == label,
                f"{key}: product says {label!r}, money says {money_view.LABELS.get(key)!r}")
    withdrawn = ("Their cut", "You keep", "Left after TikTok", "Contribution", "Return Loss")
    words = [w for s in products.SECTIONS for w in s[1:3]] + list(products.LABELS.values())
    for w in words:
        _assert(not any(x.lower() in w.lower() for x in withdrawn), f"withdrawn label: {w}")
check("Product and Money calculators use A8's words and no withdrawn label", product_and_money_use_the_same_words)


# --- who is signed in, and which shops
from app import me

def me_and_shops():
    acct = (ACCOUNT.id, "owner@synthetic-uk-shop.test", "Synthetic UK Shop Ltd", "en-GB",
            "Europe/London", "active", NOW, None, 1)
    shop = (SHOP, "tiktok_shop", "7495000000000000001", None, "Synthetic UK Shop", "GB",
            None, "GBP", "connected", None, None)
    me.tenant = with_conn(me, [
        ("from accounts a", Result(["id","email","display_name","locale","timezone","status",
                                    "created_at","deletion_scheduled_at","shop_count"], [acct])),
        ("from shops where connection_status", Result(["id","platform","tiktok_shop_id",
            "tiktok_shop_code","shop_name","region","seller_type","currency",
            "connection_status","first_synced_at","last_synced_at"], [shop])),
    ])
    r = client.get("/v1/me")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    _assert(r.json()["shop_count"] == 1 and "ETag" in r.headers)
    r2 = client.get("/v1/me", headers={"If-None-Match": r.headers["ETag"]})
    _assert(r2.status_code == 304, f"expected 304, got {r2.status_code}")
    s = client.get("/v1/shops")
    _assert(s.status_code == 200, f"status {s.status_code}: {s.text[:300]}")
    b = s.json()["shops"][0]
    _assert(b["id"] == str(SHOP) and b["authorization_expires_at"] is None, b)
check("GET me and shops return the caller's own rows with an ETag", me_and_shops)


# --- cost prices
from app import costs

def put_cost_supersedes():
    prev = UUID("d08179cb-76e4-ad96-2847-829e1d5cdc95")
    costs.tenant = with_conn(costs, [
        ("from skus k join shops s", Result(["c"], [("GBP",)])),
        ("update product_costs set superseded_at", Result(["id"], [(prev,)])),
        ("insert into product_costs", Result([], [])),
    ])
    r = client.put(f"/v1/shops/{SHOP}/skus/{SKU}/cost",
                   json={"cost": {"amount_minor": 3600, "currency": "GBP"}})
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    _assert(b["supersedes"] == str(prev) and b["source"] == "manual", b)
    _assert(b["cost"]["amount_minor"] == 3600)
    bad = client.put(f"/v1/shops/{SHOP}/skus/{SKU}/cost",
                     json={"cost": {"amount_minor": 3600, "currency": "USD"}})
    _assert(bad.status_code == 422, f"a USD cost on a GBP shop gave {bad.status_code}")
    neg = client.put(f"/v1/shops/{SHOP}/skus/{SKU}/cost",
                     json={"cost": {"amount_minor": -1, "currency": "GBP"}})
    _assert(neg.status_code == 422)
    costs.tenant = with_conn(costs, [("from skus k join shops s", Result(["c"], []))])
    nf = client.put(f"/v1/shops/{SHOP}/skus/{SKU}/cost",
                    json={"cost": {"amount_minor": 1, "currency": "GBP"}})
    _assert(nf.status_code == 404 and nf.json()["code"] == "sku_not_found")
check("PUT cost supersedes the current cost and refuses a wrong currency", put_cost_supersedes)

def coverage():
    cols = ["sku_id","product_title","units","units_costed","gross_minor","has_cost","currency"]
    # The third variant's cost took effect partway through the period, so one of its four
    # units sold with a cost and three without (A31.4). It counts as missing a cost.
    rows = [(UUID(int=1), "Desk", 3, 0, 36000, False, "GBP"),
            (UUID(int=3), "Lamp", 4, 1, 8000, False, "GBP"),
            (UUID(int=2), "Brush", 7, 7, 14000, True, "GBP")]
    costs.tenant = with_conn(costs, [("with lines as", Result(cols, rows))])
    b = client.get(f"/v1/shops/{SHOP}/costs/coverage?from=2026-07-01&to=2026-08-31").json()
    _assert(b["units_total"] == 14 and b["units_with_cost"] == 8, b)
    _assert(abs(b["coverage"] - 8 / 14) < 1e-9 and b["skus_missing_cost"] == 2)
    _assert(b["top_missing"][0]["gross_sales"]["amount_minor"] == 36000)
    _assert(b["period"]["basis"] == "sales")
    costs.tenant = with_conn(costs, [("with lines as", Result(cols, []))])
    _assert(client.get(f"/v1/shops/{SHOP}/costs/coverage").json()["coverage"] == 1.0,
            "with nothing sold, nothing is uncosted")
check("GET cost coverage is the share of sold units with a cost", coverage)


# --- resolving a discrepancy, and adjusting stock
D_ID = UUID("0407a537-ca4d-627c-3829-74249d317c38")

def _disc(kind="amount", status="open", seller=None, resolution=None, note="PLATFORM_PENALTY"):
    return (D_ID, kind, "settlement", None, "adjustment_amount", "-5.00", seller, "-5.00",
            status, resolution, note, None, NOW, NOW if status == "resolved" else None)

def resolve_rules():
    class Log(Result):
        def __init__(self): super().__init__([], [])
    def answers(kind, after):
        return [
            ("delete from idempotency_keys", Result([], [])),
            ("select request_hash", Result(["h","s","r"], [])),
            ("for update", Result(DISC_COLS + ["old_seller"], [_disc(kind) + (None,)])),
            ("update discrepancies set status", Result(DISC_COLS, [after])),
            ("insert into change_log", Log()),
            ("insert into idempotency_keys", Result([], [])),
        ]
    discrepancies.tenant = with_conn(discrepancies, answers("amount", _disc(status="resolved", resolution="explained", note="Confirmed")))
    r = client.post(f"/v1/shops/{SHOP}/discrepancies/{D_ID}/resolve",
                    json={"resolution": "explained", "note": "Confirmed"},
                    headers={"Idempotency-Key": "resolve-0001"})
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    _assert(b["discrepancy"]["status"] == "resolved" and b["adjustment_posted"] is None, b)
    # A statement amount is TikTok's own fact, so it cannot be corrected (0013 ruling 3).
    r = client.post(f"/v1/shops/{SHOP}/discrepancies/{D_ID}/resolve",
                    json={"resolution": "corrected_seller", "applied_value": "-4.00"})
    _assert(r.status_code == 422 and r.json()["code"] == "not_correctable", r.text)
    # A product code is the seller's own record, so it can be, and only seller_value moves.
    discrepancies.tenant = with_conn(discrepancies, answers("product_code",
        _disc("product_code", "resolved", seller="P002", resolution="corrected_seller")))
    r = client.post(f"/v1/shops/{SHOP}/discrepancies/{D_ID}/resolve",
                    json={"resolution": "corrected_seller", "applied_value": "P002"})
    _assert(r.status_code == 200, r.text)
    _assert(r.json()["discrepancy"]["applied_value"] == "-5.00", "the applied value must not move")
    r = client.post(f"/v1/shops/{SHOP}/discrepancies/{D_ID}/resolve",
                    json={"resolution": "corrected_seller"})
    _assert(r.status_code == 422, "a correction without its value")
check("POST resolve closes the flag, never corrects a TikTok fact, and moves no money", resolve_rules)

def resolve_replays_and_refuses_reuse():
    stored = {"discrepancy": {"id": str(D_ID)}, "adjustment_posted": None}
    from app.idempotency import request_hash
    body = {"resolution": "explained", "note": "x", "applied_value": None}
    h = request_hash(str(SHOP), str(D_ID), body)
    discrepancies.tenant = with_conn(discrepancies, [
        ("delete from idempotency_keys", Result([], [])),
        ("select request_hash", Result(["h","s","r"], [(h, 200, stored)])),
    ])
    r = client.post(f"/v1/shops/{SHOP}/discrepancies/{D_ID}/resolve", json=body,
                    headers={"Idempotency-Key": "resolve-0001"})
    _assert(r.status_code == 200 and r.json() == stored, f"a repeat must return the first result: {r.text}")
    r = client.post(f"/v1/shops/{SHOP}/discrepancies/{D_ID}/resolve",
                    json={"resolution": "accepted_tiktok"}, headers={"Idempotency-Key": "resolve-0001"})
    _assert(r.status_code == 422 and r.json()["code"] == "idempotency_key_reused", r.text)
check("A repeated key returns the first result, and a reused key is refused", resolve_replays_and_refuses_reuse)

def adjustment_rules():
    move = (UUID(int=11), "manual_adjustment", -2, NOW, None, None, "Two damaged", ACCOUNT.id)
    stock.tenant = with_conn(stock, [
        # First, because the positions query also contains the text of the lock below.
        ("with settings as", Result(STOCK_COLS, [_stock_row(SKU, 17, None, "healthy")])),
        ("from stock_positions sp join skus k", Result(["on_shelf"], [(19,)])),
        ("insert into stock_movements", Result(MOVE_COLS, [move])),
        ("update stock_positions set adjusted_delta", Result([], [])),
    ])
    r = client.post(f"/v1/shops/{SHOP}/stock/{SKU}/adjustments",
                    json={"quantity": -2, "reason": "Two damaged"})
    _assert(r.status_code == 201, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    _assert(b["movement"]["quantity"] == -2 and b["position"]["on_shelf"] == 17, b)
    for bad in ({"quantity": 0, "reason": "x"}, {"quantity": 1, "reason": "  "},
                {"quantity": -20, "reason": "More than there are"}):
        r = client.post(f"/v1/shops/{SHOP}/stock/{SKU}/adjustments", json=bad)
        _assert(r.status_code == 422, f"{bad} gave {r.status_code}")
    stock.tenant = with_conn(stock, [
        ("from stock_positions sp join skus k", Result(["on_shelf"], [])),
        ("select 1 from skus", Result(["x"], [])),
    ])
    r = client.post(f"/v1/shops/{SHOP}/stock/{SKU}/adjustments", json={"quantity": 1, "reason": "x"})
    _assert(r.status_code == 404, r.text)
check("POST adjustment records a movement with its reason and refuses what it cannot count", adjustment_rules)


# --- Needs you on its own, and sync status
from app import sync_status, today_view as _tv

def needs_you_alone():
    _tv.tenant = with_conn(_tv, [
        ("returns_to_check", _needs(latest_sync_statuses=["failed"])),
        ("select trim(currency) from shops", Result(["c"], [("GBP",)])),
    ])
    r = client.get(f"/v1/shops/{SHOP}/needs-you")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    items = r.json()["items"]
    types = [i["type"] for i in items]
    # The same order as Today: warnings with money at stake first, info last (A29.6).
    _assert(types[0] == "unmapped_fees" and types[-1] in ("out_of_stock", "first_sync_pending"), types)
    hrefs = {i["type"]: i["href"] for i in items}
    _assert(hrefs["open_discrepancies"] == f"/shops/{SHOP}/discrepancies?status=open", hrefs)
    _assert(hrefs["sync_failed"] is None)
check("GET needs-you serves Today's items, order and links", needs_you_alone)

def sync_status_rules():
    from app.dates import now_utc
    now = now_utc()
    rows = [("finance", "completed", 1, 7, now - timedelta(hours=2)),
            ("orders", "failed", 2, 0, now - timedelta(hours=30)),
            ("returns", "partial", 1, 3, None)]
    sync_status.tenant = with_conn(sync_status, [
        ("from sync_runs r", Result(["domain","status","attempt","records_written","last_success_at"], rows)),
    ])
    r = client.get(f"/v1/shops/{SHOP}/sync")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    d = {x["domain"]: x for x in r.json()["domains"]}
    _assert(d["finance"]["stale"] is False, d["finance"])
    _assert(d["orders"]["stale"] is True and d["orders"]["status"] == "failed", d["orders"])
    _assert(d["returns"]["stale"] is True, "never completed is stale (A29.3)")
    _assert("overall" not in r.json(), "overall is not served, because nothing defines it")
check("GET sync reports each domain's latest run, stale after 24 hours", sync_status_rules)



def cors_is_configuration():
    # Unset, no origin is allowed and no CORS header is sent.
    r = client.options("/v1/me", headers={"Origin": "https://evil.example",
                                           "Access-Control-Request-Method": "GET"})
    _assert("access-control-allow-origin" not in {k.lower() for k in r.headers}, dict(r.headers))
check("No origin is allowed across sites unless ALLOWED_ORIGINS names it", cors_is_configuration)

# --- returns and notifications
from app import notifications as notes, returns as rets

RET_COLS = ["id","tiktok_return_id","tiktok_order_id","tiktok_credit_note_number","kind","status",
            "reason_code","refund_minor","requested_at","refund_completed_at","items_awaiting_check",
            "return_cost_minor","write_off_minor","cost_entries","sort_at","currency"]

def returns_list():
    rows = [(UUID(int=i), f"RETA{i}", "5767", None, "return_refund", "COMPLETE", "Damaged",
             -12000, NOW, NOW, 0, 0, -5100, 1, NOW, "GBP") for i in (16, 15)]
    rows[1] = rows[1][:11] + (0, 0, 0, NOW, "GBP")
    rets.tenant = with_conn(rets, [
        ("from returns r join return_reconciliation", Result(RET_COLS, rows)),
        ("from return_items where shop_id", Result(["c"], [(3,)])),
        ("from return_items ri left join skus", Result(
            ["id","return_id","sku_id","quantity","seller_check_status","checked_at","return_postage_minor","title","variant_label"],
            [(UUID(int=99), UUID(int=16), SKU, 1, "pending", None, None, "Desk", "Black")])),
    ])
    r = client.get(f"/v1/shops/{SHOP}/returns?limit=1")
    _assert(r.status_code == 200, f"status {r.status_code}: {r.text[:300]}")
    b = r.json()
    _assert(b["awaiting_check_count"] == 3 and b["next_cursor"], b)
    _assert(b["returns"][0]["items"][0]["id"] == str(UUID(int=99)) and b["returns"][0]["items"][0]["product_title"] == "Desk",
            "each return carries its items, so S8 can check them by id")
    _assert(b["returns"][0]["return_cost"]["amount_minor"] == 5100, "return costs are the amount lost (A4.2)")
    _assert(b["returns"][0]["refund"]["amount_minor"] == -12000, "the refund keeps its sign")
    b2 = client.get(f"/v1/shops/{SHOP}/returns").json()
    _assert(b2["returns"][1]["return_cost"] is None, "nothing posted is not the same as zero")
check("GET returns carries each return's refund and return costs", returns_list)

def return_metrics():
    rows = [("product", UUID(int=1), "Desk", 1, 5100, None, None),
            ("product", UUID(int=2), "Brush", 3, 0, None, None),
            ("totals", None, None, 7, 5550, 24, 5100)]
    rets.tenant = with_conn(rets, [
        ("with returned as", Result(["row_kind","product_id","title","units","lost","sold_units","written_off"], rows)),
        ("select trim(currency) from shops", Result(["c"], [("GBP",)])),
    ])
    b = client.get(f"/v1/shops/{SHOP}/returns/metrics?from=2026-07-01&to=2026-08-31").json()
    _assert(abs(b["return_rate"] - 7 / 24) < 1e-9 and b["returns_units"] == 7, b)
    _assert(b["total_return_cost"]["amount_minor"] == 5550 and b["write_off_total"]["amount_minor"] == 5100)
    _assert(b["most_returned"][0]["title"] == "Brush", "most units first")
    rows[-1] = ("totals", None, None, 9, 0, 4, 0)
    rets.tenant = with_conn(rets, [
        ("with returned as", Result(["row_kind","product_id","title","units","lost","sold_units","written_off"], rows)),
        ("select trim(currency) from shops", Result(["c"], [("GBP",)])),
    ])
    _assert(client.get(f"/v1/shops/{SHOP}/returns/metrics").json()["return_rate"] == 1.0,
            "more returns than sales is capped at the contract's bound")
check("GET return metrics divides returned units by units sold", return_metrics)

NOTE_COLS = ["id","shop_id","type","severity","title","body","entity_type","entity_id","status","created_at"]

def notifications_rules():
    n = (UUID(int=5), SHOP, "out_of_stock", "info", "Seasonal Gift Box is out of stock",
         None, None, None, "unread", NOW)
    notes.tenant = with_conn(notes, [
        ("from notifications where account_id = %s and status = 'unread'", Result(["c"], [(4,)])),
        ("from notifications where account_id", Result(NOTE_COLS, [n])),
    ])
    b = client.get("/v1/notifications?status=unread").json()
    _assert(b["unread_count"] == 4 and b["notifications"][0]["type"] == "out_of_stock", b)
    # Open is unread and read together, filtered by the service rather than the browser.
    notes.tenant = with_conn(notes, [
        ("status = 'unread'", Result(["c"], [(4,)])),
        ("status <> 'done'", Result(NOTE_COLS, [n])),
    ])
    r = client.get("/v1/notifications?status=open")
    _assert(r.status_code == 200 and r.json()["notifications"][0]["status"] == "unread", r.text)
    notes.tenant = with_conn(notes, [
        ("for update", Result(["status"], [("done",)])),
    ])
    r = client.patch(f"/v1/notifications/{UUID(int=5)}", json={"status": "read"})
    _assert(r.status_code == 422, "done cannot go back to read")
    r = client.patch(f"/v1/notifications/{UUID(int=5)}", json={"status": "unread"})
    _assert(r.status_code == 422, "nothing goes back to unread")
    notes.tenant = with_conn(notes, [
        ("for update", Result(["status"], [("unread",)])),
        ("update notifications set status", Result(NOTE_COLS, [n[:8] + ("read", NOW)])),
    ])
    r = client.patch(f"/v1/notifications/{UUID(int=5)}", json={"status": "read"})
    _assert(r.status_code == 200 and r.json()["status"] == "read", r.text)
    notes.tenant = with_conn(notes, [("for update", Result(["status"], []))])
    _assert(client.patch(f"/v1/notifications/{UUID(int=5)}", json={"status": "read"}).status_code == 404)
check("Notifications list with an unread count, and move one way only", notifications_rules)


# --- cost uploads (CST-2). The store is replaced by a dictionary, because CI has no bucket.
from app import cost_uploads as cu, storage as store

UPLOAD = UUID("44444444-4444-4444-8444-444444444444")
UP_KEY = f"uploads/{SHOP}/{UPLOAD}/nonce/costs.csv"
UP_COLS = ["id", "filename", "storage_key", "status", "column_mapping", "rows_total",
           "rows_matched", "rows_unmatched", "rows_duplicate", "confirmed_at", "created_at"]


def upload_row(status, mapping=None):
    return (UPLOAD, "costs.csv", UP_KEY, status, mapping, None, None, None, None, None, NOW)


def uploads_without_a_bucket():
    os.environ.pop("S3_BUCKET", None)
    # No canned answer at all: an insert reached before the refusal would raise KeyError.
    cu.tenant = with_conn(cu, [])
    r = client.post(f"/v1/shops/{SHOP}/cost-uploads",
                    json={"filename": "costs.csv", "content_type": "text/csv", "size_bytes": 10})
    _assert(r.status_code == 503 and r.json()["code"] == "storage_unconfigured", r.text)
check("A cost upload without a bucket answers 503 and writes nothing", uploads_without_a_bucket)


def uploads_map_match_apply():
    files = {UP_KEY: b"Seller SKU,Unit cost\nHAIR-BLUE,3.50\nNOPE,1.00\n"}
    store.size_of = lambda k: len(files[k]) if k in files else (_ for _ in ()).throw(store.NotStored(k))
    store.get_bytes = lambda k: files[k] if k in files else (_ for _ in ()).throw(store.NotStored(k))
    store.put_bytes = lambda k, d, t: files.__setitem__(k, d)
    mapping = {"match_on": "seller_sku", "key_column": "Seller SKU", "cost_column": "Unit cost",
               "packing_column": None, "postage_column": None, "currency": "GBP"}
    cu.tenant = with_conn(cu, [
        ("from cost_uploads where id", Result(UP_COLS, [upload_row("mapped", mapping)])),
        ("from shops where id", Result(["c"], [("GBP",)])),
        ("update cost_uploads set column_mapping", Result([], [])),
    ])
    r = client.put(f"/v1/shops/{SHOP}/cost-uploads/{UPLOAD}/mapping", json=mapping)
    _assert(r.status_code == 200 and r.json()["detected_columns"] == ["Seller SKU", "Unit cost"], r.text)
    r = client.put(f"/v1/shops/{SHOP}/cost-uploads/{UPLOAD}/mapping", json={**mapping, "currency": "USD"})
    _assert(r.status_code == 422, "a mapping in another currency is refused")
    cu.tenant = with_conn(cu, [
        ("from cost_uploads where id", Result(UP_COLS, [upload_row("mapped", mapping)])),
        ("from skus where shop_id", Result(["id", "seller_sku", "tiktok_sku_id"], [(SKU, "HAIR-BLUE", "1729")])),
        ("update cost_uploads set status = 'confirmed'", Result([], [])),
    ])
    r = client.post(f"/v1/shops/{SHOP}/cost-uploads/{UPLOAD}/match")
    _assert(r.status_code == 200, r.text)
    m = r.json()
    _assert((m["rows_total"], m["rows_matched"], m["rows_unmatched"]) == (2, 1, 1), m)
    _assert(UP_KEY.rsplit("/", 1)[0] + "/rows.json" in files, "the match is stored beside the file")
    hit = [x["row_id"] for x in m["rows"] if x["outcome"] == "matched"]
    miss = [x["row_id"] for x in m["rows"] if x["outcome"] == "unmatched"]
    writes = []
    class Recording(Conn):
        def execute(self, sql, args=None):
            if "product_costs" in sql: writes.append(" ".join(sql.split())[:30])
            return super().execute(sql, args)
    import contextlib
    @contextlib.contextmanager
    def rec(_a):
        yield Recording([
            ("from cost_uploads where id", Result(UP_COLS, [upload_row("confirmed", mapping)])),
            ("from shops where id", Result(["c"], [("GBP",)])),
            ("update product_costs", Result([], [])),
            ("insert into product_costs", Result([], [])),
            ("update cost_uploads set status = 'applied'", Result([], [])),
        ])
    cu.tenant = rec
    r = client.post(f"/v1/shops/{SHOP}/cost-uploads/{UPLOAD}/apply", json={"apply_row_ids": miss})
    _assert(r.status_code == 422 and not writes, "an unmatched row is refused before anything is written")
    r = client.post(f"/v1/shops/{SHOP}/cost-uploads/{UPLOAD}/apply", json={"apply_row_ids": hit})
    _assert(r.status_code == 200 and r.json()["rows_total"] == 2, "every row stays visible after apply")
    _assert([w.split(" product_costs")[0] for w in writes] == ["update", "insert into"], writes)
check("A cost upload maps, matches and applies only the confirmed matched rows", uploads_map_match_apply)


# --- checkReturnItem (RET-3, RET-4, A30.2)

ITEM = UUID("55555555-5555-4555-8555-555555555555")
RET = UUID("66666666-6666-4666-8666-666666666666")
ORDER = UUID("77777777-7777-4777-8777-777777777777")
LINE = UUID("88888888-8888-4888-8888-888888888888")
ITEM_COLS = ["id", "return_id", "sku_id", "quantity", "seller_check_status", "order_id", "currency"]


def return_check():
    import contextlib
    writes = []
    class Rec(Conn):
        def execute(self, sql, args=None):
            flat = " ".join(sql.split())
            if flat.startswith(("insert", "update")): writes.append(flat[:40])
            return super().execute(sql, args)
    def make(status):
        @contextlib.contextmanager
        def fake(_a):
            yield Rec([
                ("from return_items ri join returns", Result(ITEM_COLS, [(ITEM, RET, SKU, 1, status, ORDER, "GBP")])),
                ("from order_lines ol join orders", Result(["id", "d"], [(LINE, date(2026, 8, 3))])),
                ("from product_costs", Result(["cost_minor"], [(324,)])),
                ("insert into ledger_entries", Result([], [])),
                ("insert into stock_movements", Result([], [])),
                ("update stock_positions", Result([], [])),
                ("update return_items", Result(["id", "return_id", "sku_id", "quantity", "seller_check_status", "checked_at", "return_postage_minor"],
                                               [(ITEM, RET, SKU, 1, "unsellable", NOW, 285)])),
            ])
        return fake
    url = f"/v1/shops/{SHOP}/return-items/{ITEM}/check"
    rets.tenant = make("pending")
    r = client.post(url, json={"seller_check_status": "unsellable", "return_postage": {"amount_minor": 285, "currency": "GBP"}})
    _assert(r.status_code == 200, r.text)
    _assert(r.json()["write_off"]["amount_minor"] == 324 and r.json()["stock_movements_created"] == 0, r.json())
    _assert(sum(w.startswith("insert into ledger_entries") for w in writes) == 2, writes)
    _assert(not any(w.startswith("insert into stock_movements") for w in writes), "unsellable makes no movement")
    writes.clear()
    rets.tenant = make("resellable")
    r = client.post(url, json={"seller_check_status": "resellable"})
    _assert(r.status_code == 409 and not writes, "a checked item is refused before anything is written")
    r = client.post(url, json={"seller_check_status": "not_applicable", "return_postage": {"amount_minor": 1, "currency": "GBP"}})
    _assert(r.status_code == 422, "postage on nothing-came-back is refused")
check("checkReturnItem writes a write-off and postage, and refuses a second check", return_check)


# --- account deletion (A30.1)
from app import account_deletion as deletion

def delete_and_cancel():
    from app import billing as _billing
    saved_row = _billing.db.get_subscription_row
    _billing.db.get_subscription_row = lambda _a: None  # no plan: Stripe is never called
    try:
        _delete_and_cancel()
    finally:
        _billing.db.get_subscription_row = saved_row

def _delete_and_cancel():
    writes = []
    def make(status):
        import contextlib
        @contextlib.contextmanager
        def fake(_a):
            class C(Conn):
                def execute(self, sql, args=None):
                    flat = " ".join(sql.split())
                    if flat.startswith("update"): writes.append(flat[:40])
                    return super().execute(sql, args)
            yield C([
                ("from accounts where id", Result(["email", "status", "deleted_at"], [(ACCOUNT.email, status, NOW)])),
                ("update accounts set status = 'deleted'", Result(["deleted_at"], [(NOW,)])),
                ("update tiktok_connections", Result([], [])),
                ("update shops", Result([], [])),
                ("from tiktok_invoices", Result(["m"], [(date(2026, 6, 30),)])),
                ("update accounts set status = 'active'", Result(["id"], [(ACCOUNT.id,)] if status == "deleted" else [])),
                ("select count(*) from shops", Result(["n"], [(1,)])),
            ])
        return fake
    deletion.tenant = make("active")
    r = client.request("DELETE", "/v1/me", json={"confirm_email": "someone@else.test"})
    _assert(r.status_code == 422 and not writes, "a wrong email is refused before anything is written")
    r = client.request("DELETE", "/v1/me", json={"confirm_email": ACCOUNT.email.upper()})
    _assert(r.status_code == 202, r.text)
    b = r.json()
    _assert(b["scheduled_at"].startswith("2026-09-14") and b["cancel_by"] == b["scheduled_at"], b)
    _assert(b["invoices_retained_until"] == "2032-06-30" and len(b["includes"]) == 5, b)
    _assert(len(writes) == 3, writes)
    writes.clear()
    deletion.tenant = make("deleted")
    r = client.request("DELETE", "/v1/me", json={"confirm_email": ACCOUNT.email})
    _assert(r.status_code == 202 and not writes, "a repeat keeps the first dates and writes nothing")
    r = client.post("/v1/me/deletion/cancel")
    _assert(r.status_code == 200 and r.json()["shops_disconnected"] == 1, r.text)
    deletion.tenant = make("active")
    _assert(client.post("/v1/me/deletion/cancel").status_code == 409, "nothing to cancel")

    # A seller with a plan is told it stops renewing, and a Stripe failure deletes nothing.
    from app.problems import Problem as _P
    saved_set = deletion.billing.set_renewal_for_deletion
    try:
        writes.clear()
        deletion.billing.set_renewal_for_deletion = lambda _a, closing: "stopped"
        r = client.request("DELETE", "/v1/me", json={"confirm_email": ACCOUNT.email})
        _assert(r.status_code == 202 and len(r.json()["includes"]) == 6
                and "stops renewing" in r.json()["includes"][2], r.text)
        writes.clear()
        def down(_a, closing): raise _P(502, "stripe_error", "x")
        deletion.billing.set_renewal_for_deletion = down
        r = client.request("DELETE", "/v1/me", json={"confirm_email": ACCOUNT.email})
        _assert(r.status_code == 502 and not writes, f"{r.status_code} {writes}")
    finally:
        deletion.billing.set_renewal_for_deletion = saved_set
check("deleteMe closes the account with dates, and cancelAccountDeletion reopens it", delete_and_cancel)


# --- startTrial never makes a second subscription for one account (audit H2)
from app import billing

def trial_once():
    from types import SimpleNamespace as NS
    created = []

    class Subs:
        def __init__(self, open_subs): self.open_subs = open_subs
        def list(self, params): return NS(data=self.open_subs)
        def create(self, params, options=None):
            created.append(params)
            return NS(id="sub_new", status="trialing", trial_end=1790000000,
                      pending_setup_intent=NS(client_secret="seti_new_secret"),
                      get=lambda k, d=None: {"customer": "cus_1", "id": "sub_new", "status": "trialing"}.get(k, d))

    class Customers:
        def retrieve(self, cid): return NS(id=cid)
        def search(self, params): return NS(data=[])
        def create(self, params, options=None): return NS(id="cus_1")

    def client_with(open_subs):
        return NS(subscriptions=Subs(open_subs), customers=Customers())

    os.environ["STRIPE_PRICE_STARTER"] = "price_test"
    saved = (billing._stripe, billing.db.get_subscription_row, billing.db.create_subscription_row,
             billing._apply_stripe_subscription)
    billing.db.create_subscription_row = lambda *a: None
    billing._apply_stripe_subscription = lambda sub: None
    try:
        for status in ("trialing", "active", "past_due"):
            billing.db.get_subscription_row = lambda _a, s=status: {"status": s, "stripe_customer_id": "cus_1"}
            billing._stripe = lambda: client_with([])
            r = client.post("/v1/billing/subscription", json={"plan": "starter"})
            _assert(r.status_code == 409 and not created, f"{status}: {r.status_code} {r.text[:120]}")

        open_sub = NS(id="sub_old", status="incomplete", trial_end=1790000000,
                      pending_setup_intent=NS(client_secret="seti_old_secret"))
        billing.db.get_subscription_row = lambda _a: {"status": "incomplete", "stripe_customer_id": "cus_1"}
        billing._stripe = lambda: client_with([open_sub])
        r = client.post("/v1/billing/subscription", json={"plan": "starter"})
        _assert(r.status_code == 200 and r.json()["subscription_id"] == "sub_old"
                and r.json()["client_secret"] == "seti_old_secret" and not created, r.text)

        billing.db.get_subscription_row = lambda _a: None
        billing._stripe = lambda: client_with([])
        r = client.post("/v1/billing/subscription", json={"plan": "starter"})
        _assert(r.status_code == 200 and r.json()["subscription_id"] == "sub_new" and len(created) == 1, r.text)
    finally:
        (billing._stripe, billing.db.get_subscription_row, billing.db.create_subscription_row,
         billing._apply_stripe_subscription) = saved
check("startTrial refuses a live subscription, reuses an unfinished one, and starts a first", trial_once)


# --- a Stripe refusal is logged with Stripe's reason, and the seller still sees the plain 502
# (8 October 2026: seven refusals on 7 October left no reason anywhere)
def stripe_refusal_logged():
    import logging
    from types import SimpleNamespace as NS
    import stripe as _stripe_mod

    class Customers:
        def search(self, params):
            raise _stripe_mod.PermissionError(
                "The provided key does not have the required permissions.",
                http_status=403,
                json_body={"error": {"type": "invalid_request_error", "code": "secret_key_required",
                                     "message": "The provided key does not have the required permissions."}},
                headers={"request-id": "req_test"},
                code="secret_key_required",
            )

    records = []
    handler = logging.Handler()
    handler.emit = records.append
    log = logging.getLogger("myshopedge.billing")
    log.addHandler(handler)
    os.environ["STRIPE_PRICE_STARTER"] = "price_test"
    saved = (billing._stripe, billing.db.get_subscription_row)
    billing._stripe = lambda: NS(customers=Customers())
    billing.db.get_subscription_row = lambda _a: None
    try:
        r = client.post("/v1/billing/subscription", json={"plan": "starter"})
        _assert(r.status_code == 502 and r.json()["detail"] ==
                "We could not start the trial. Nobody has been charged.", r.text)
        line = records[-1].getMessage() if records else ""
        for part in ("find_or_create_customer", "PermissionError", "http=403", "type=invalid_request_error",
                     "code=secret_key_required", "request=req_test", "required permissions"):
            _assert(part in line, f"{part!r} missing from {line!r}")
    finally:
        log.removeHandler(handler)
        billing._stripe, billing.db.get_subscription_row = saved
check("a Stripe refusal is logged with its step, type, code and request id", stripe_refusal_logged)


# --- real Stripe objects reach the readers (8 October 2026: stripe-python 16 objects have no
# .get, the stand-ins above did, and every live trial start failed after Stripe had made it)
def real_stripe_objects_read():
    from types import SimpleNamespace as NS
    import stripe as _stripe_mod

    def real_sub(**over):
        data = {"object": "subscription", "id": "sub_real", "customer": "cus_real",
                "status": "incomplete", "trial_end": 1792000000, "cancel_at_period_end": False,
                "metadata": {"plan": "starter", "account_id": "a"},
                "items": {"object": "list", "data": [{"object": "subscription_item",
                          "price": {"object": "price", "id": "price_test"},
                          "current_period_start": 1790000000, "current_period_end": 1792000000}]},
                "pending_setup_intent": {"object": "setup_intent", "id": "seti_1",
                                         "client_secret": "seti_1_secret_x"}}
        data.update(over)
        return _stripe_mod.Subscription.construct_from(data, "sk_test_x")

    written = []

    class Subs:
        def create(self, params, options=None): return real_sub()
        def list(self, params): return NS(data=[])
        def retrieve(self, sid): return real_sub(status="trialing")
        def update(self, sid, params): return real_sub(status="trialing", **params)

    class Customers:
        def search(self, params): return NS(data=[])
        def create(self, params, options=None): return NS(id="cus_real")

    os.environ["STRIPE_PRICE_STARTER"] = "price_test"
    saved = (billing._stripe, billing.db.get_subscription_row, billing.db.create_subscription_row,
             billing.db.apply_subscription_event)
    billing._stripe = lambda: NS(subscriptions=Subs(), customers=Customers())
    billing.db.create_subscription_row = lambda *a: None
    billing.db.apply_subscription_event = lambda **kw: written.append(kw)
    try:
        billing.db.get_subscription_row = lambda _a: None
        r = client.post("/v1/billing/subscription", json={"plan": "starter"})
        _assert(r.status_code == 200 and r.json()["client_secret"] == "seti_1_secret_x", r.text)
        w = written[-1]
        _assert(w["stripe_customer_id"] == "cus_real" and w["plan_slug"] == "starter"
                and w["status"] == "incomplete" and w["period_end"] is not None, w)

        billing.db.get_subscription_row = lambda _a: {"status": "trialing", "stripe_customer_id": "cus_real",
                                                      "stripe_subscription_id": "sub_real"}
        _assert(billing.set_renewal_for_deletion(ACCOUNT.id, True) == "stopped", "renewal")
    finally:
        (billing._stripe, billing.db.get_subscription_row, billing.db.create_subscription_row,
         billing.db.apply_subscription_event) = saved
check("startTrial and the renewal switch read real stripe-python objects", real_stripe_objects_read)


# --- stopping renewal and changing the card from Settings (8 October 2026)
def renewal_and_card_change():
    from types import SimpleNamespace as NS
    import stripe as _stripe_mod

    calls = []

    def real_sub(**over):
        data = {"object": "subscription", "id": "sub_real", "customer": "cus_real", "status": "trialing",
                "trial_end": 1792000000, "cancel_at_period_end": False, "metadata": {"plan": "starter"}}
        data.update(over)
        return _stripe_mod.Subscription.construct_from(data, "sk_test_x")

    def real_intent(**over):
        data = {"object": "setup_intent", "id": "seti_9", "customer": "cus_real", "status": "succeeded",
                "payment_method": "pm_9", "client_secret": "seti_9_secret_z"}
        data.update(over)
        return _stripe_mod.SetupIntent.construct_from(data, "sk_test_x")

    intent = {"value": real_intent()}

    class Subs:
        def update(self, sid, params):
            calls.append(("sub.update", sid, params))
            return real_sub(cancel_at_period_end=params.get("cancel_at_period_end", False))

    class Intents:
        def create(self, params): calls.append(("si.create", params)); return real_intent(status="requires_payment_method")
        def retrieve(self, sid): calls.append(("si.retrieve", sid)); return intent["value"]

    class Customers:
        def update(self, cid, params): calls.append(("cus.update", cid, params)); return NS(id=cid)

    state = {"row": {"plan_slug": "starter", "status": "trialing", "stripe_customer_id": "cus_real",
                     "stripe_subscription_id": "sub_real", "trial_end": None, "current_period_end": None,
                     "cancel_at_period_end": False}}

    def apply(**kw):
        state["row"] = dict(state["row"], cancel_at_period_end=kw["cancel_at_period_end"])

    saved = (billing._stripe, billing.db.get_subscription_row, billing.db.apply_subscription_event)
    billing._stripe = lambda: NS(subscriptions=Subs(), setup_intents=Intents(), customers=Customers())
    billing.db.get_subscription_row = lambda _a: state["row"]
    billing.db.apply_subscription_event = apply
    try:
        r = client.patch("/v1/billing/subscription", json={"cancel_at_period_end": True})
        _assert(r.status_code == 200 and r.json()["cancel_at_period_end"] is True, r.text)
        _assert(calls[-1] == ("sub.update", "sub_real", {"cancel_at_period_end": True}), calls[-1])
        r = client.patch("/v1/billing/subscription", json={"cancel_at_period_end": False})
        _assert(r.status_code == 200 and r.json()["cancel_at_period_end"] is False, r.text)
        _assert(calls[-1][2]["metadata"] == {billing.DELETION_FLAG: ""}, calls[-1])

        r = client.post("/v1/billing/card")
        _assert(r.status_code == 200 and r.json()["client_secret"] == "seti_9_secret_z", r.text)
        _assert(calls[-1][1]["customer"] == "cus_real" and calls[-1][1]["usage"] == "off_session", calls[-1])

        n = len(calls)
        r = client.put("/v1/billing/card", json={"setup_intent_id": "seti_9"})
        _assert(r.status_code == 200, r.text)
        _assert(("cus.update", "cus_real", {"invoice_settings": {"default_payment_method": "pm_9"}}) in calls[n:], calls[n:])
        _assert(("sub.update", "sub_real", {"default_payment_method": "pm_9"}) in calls[n:], calls[n:])

        for bad in (real_intent(customer="cus_other"), real_intent(status="requires_action")):
            intent["value"] = bad
            n = len(calls)
            r = client.put("/v1/billing/card", json={"setup_intent_id": "seti_9"})
            _assert(r.status_code == 409 and r.json()["code"] == "card_not_confirmed", r.text)
            _assert(not any(c[0] in ("cus.update", "sub.update") for c in calls[n:]), "nothing may change")

        for row, code in ((None, "no_live_subscription"),
                          (dict(state["row"], status="canceled"), "no_live_subscription"),
                          (dict(state["row"], stripe_customer_id="demo_1"), "demo_subscription")):
            billing.db.get_subscription_row = lambda _a, r_=row: r_
            n = len(calls)
            r = client.patch("/v1/billing/subscription", json={"cancel_at_period_end": True})
            _assert(r.status_code == 409 and r.json()["code"] == code and len(calls) == n, r.text)
    finally:
        billing._stripe, billing.db.get_subscription_row, billing.db.apply_subscription_event = saved
check("renewal can be stopped and restored, and the card changed, only on a live plan", renewal_and_card_change)


# --- a deletion stops renewal, and cancelling it restores only what it stopped (7 October 2026)
def renewal_follows_deletion():
    from types import SimpleNamespace as NS
    import stripe as _stripe_mod
    calls = []

    class Sub(dict):
        pass

    state = {"cancel_at_period_end": False, "metadata": {}}

    class Subs:
        fail = False
        def retrieve(self, sid):
            if Subs.fail: raise _stripe_mod.APIConnectionError("down")
            return Sub(id=sid, customer="cus_1", status="trialing", **state)
        def update(self, sid, params):
            calls.append(params)
            state["cancel_at_period_end"] = params["cancel_at_period_end"]
            meta = dict(state["metadata"])
            for k, v in params["metadata"].items():
                if v == "": meta.pop(k, None)
                else: meta[k] = v
            state["metadata"] = meta
            return Sub(id=sid, customer="cus_1", status="trialing", **state)

    saved = (billing._stripe, billing.db.get_subscription_row, billing._apply_stripe_subscription)
    billing._stripe = lambda: NS(subscriptions=Subs())
    billing._apply_stripe_subscription = lambda sub: None
    live = {"status": "trialing", "stripe_customer_id": "cus_1", "stripe_subscription_id": "sub_1"}
    try:
        billing.db.get_subscription_row = lambda _a: None
        _assert(billing.set_renewal_for_deletion(ACCOUNT.id, True) == "none" and not calls, "no plan")
        billing.db.get_subscription_row = lambda _a: dict(live, stripe_customer_id="demo_x")
        _assert(billing.set_renewal_for_deletion(ACCOUNT.id, True) == "none" and not calls, "demo")
        billing.db.get_subscription_row = lambda _a: dict(live, status="canceled")
        _assert(billing.set_renewal_for_deletion(ACCOUNT.id, True) == "none" and not calls, "canceled")

        billing.db.get_subscription_row = lambda _a: live
        _assert(billing.set_renewal_for_deletion(ACCOUNT.id, True) == "stopped", "stop")
        _assert(calls[-1] == {"cancel_at_period_end": True,
                              "metadata": {billing.DELETION_FLAG: "true"}}, calls)
        _assert(billing.set_renewal_for_deletion(ACCOUNT.id, False) == "restored", "restore")
        _assert(state == {"cancel_at_period_end": False, "metadata": {}}, state)

        # A seller who had already stopped renewal keeps that choice through a deletion and
        # its cancellation.
        calls.clear()
        state.update(cancel_at_period_end=True, metadata={})
        _assert(billing.set_renewal_for_deletion(ACCOUNT.id, True) == "unchanged", "already off")
        _assert(billing.set_renewal_for_deletion(ACCOUNT.id, False) == "unchanged" and not calls,
                "a seller's own choice is not undone")

        state.update(cancel_at_period_end=False, metadata={})
        Subs.fail = True
        try:
            billing.set_renewal_for_deletion(ACCOUNT.id, True)
            _assert(False, "a Stripe failure must raise")
        except Exception as exc:  # noqa: BLE001
            _assert(getattr(exc, "status_code", None) == 502 and exc.code == "stripe_error", repr(exc))
    finally:
        billing._stripe, billing.db.get_subscription_row, billing._apply_stripe_subscription = saved
check("a deletion stops renewal at period end, and its cancellation restores only that", renewal_follows_deletion)


# --- getExpectedPayouts groups TikTok's unsettled transactions by London week (7 October 2026)
from app import payouts

def expected_payouts():
    import contextlib
    from app.tiktok_api import TikTokError
    # Shaped on the response example from TikTok's Get Unsettled Transactions page, in GBP.
    # 1685548800 is Wednesday 31 May 2023 16:00 UTC, so its London week begins 29 May.
    page = {"next_page_token": "", "transactions": [
        {"type": "ORDER", "id": "t1", "currency": "GBP", "estimated_settlement": "1685548800",
         "order_id": "576463220456522968", "est_settlement_amount": "130"},
        {"type": "ORDER", "id": "t2", "currency": "GBP", "estimated_settlement": "1685548800",
         "order_id": "576463220456522968", "est_settlement_amount": "0.45"},
        {"type": "ADJUSTMENT", "id": "t3", "currency": "GBP", "estimated_settlement": "1686153600",
         "order_id": "", "est_settlement_amount": "-6.99"},
        {"type": "ORDER", "id": "t4", "currency": "GBP", "estimated_settlement": "",
         "order_id": "9", "est_settlement_amount": "50"},
    ]}
    asked = []
    class Client:
        def pages(self, method, path, query):
            asked.append((method, path, query))
            yield page

    weeks, undated = payouts.group_by_week(page["transactions"])
    _assert([str(w.week_starting) for w in weeks] == ["2023-05-29", "2023-06-05"], weeks)
    _assert(weeks[0].amount.amount_minor == 13045 and weeks[0].orders == 1, weeks[0])
    _assert(weeks[1].amount.amount_minor == -699 and weeks[1].orders == 0, weeks[1])
    _assert(undated == 1, undated)
    try:
        payouts.group_by_week([{"currency": "USD", "estimated_settlement": "1685548800",
                                "est_settlement_amount": "1"}])
        _assert(False, "a currency other than the shop's must be refused")
    except Exception as exc:  # noqa: BLE001
        _assert(getattr(exc, "code", "") == "tiktok_currency", repr(exc))

    @contextlib.contextmanager
    def fake(_a):
        yield Conn([("select currency from shops", Result(["currency"], [("GBP",)]))])
    saved = (payouts.tenant, payouts.client_for)
    payouts.tenant = fake
    try:
        payouts.client_for = lambda conn, sid: Client()
        r = client.get(f"/v1/shops/{SHOP}/payouts/expected")
        _assert(r.status_code == 200, r.text)
        b = r.json()
        _assert(b["confidence"] == "estimated" and b["total"]["amount_minor"] == 12346
                and len(b["weeks"]) == 2, b)
        _assert(asked[-1] == ("GET", payouts.UNSETTLED_PATH,
                              {"sort_field": "order_create_time", "sort_order": "ASC"}), asked)

        def none(conn, sid): raise TikTokError("no_connection", "x")
        payouts.client_for = none
        _assert(client.get(f"/v1/shops/{SHOP}/payouts/expected").status_code == 409, "no connection")

        class Refusing:
            def pages(self, *a):
                raise TikTokError("36009003", "Internal error")
                yield  # pragma: no cover
        payouts.client_for = lambda conn, sid: Refusing()
        r = client.get(f"/v1/shops/{SHOP}/payouts/expected")
        _assert(r.status_code == 502 and "tiktok_error" in r.text, r.text)
    finally:
        payouts.tenant, payouts.client_for = saved
check("getExpectedPayouts groups unsettled transactions by London week and labels them estimated", expected_payouts)


# --- the VAT monitor follows gov.uk's "More than £90,000" (7 October 2026)
from app import tax as tax_mod

def vat_threshold_is_more_than():
    import contextlib
    from app.dates import business_today
    month = business_today().strftime("%Y-%m")
    def make(turnover):
        @contextlib.contextmanager
        def fake(_a):
            yield Conn([
                ("from ledger_entries", Result(["m", "g"], [(month, turnover)])),
                ("from other_channel_sales where shop_id = %s and month", Result(["m", "g"], [])),
                ("select exists", Result(["e"], [(False,)])),
                ("from reference_rules", Result(["k", "v", "r"], [
                    ("registration_threshold", {"amount_minor": 9000000, "currency": "GBP"}, None)])),
            ])
        return fake
    saved = tax_mod.tenant
    try:
        for turnover, over in ((8999999, False), (9000000, False), (9000001, True)):
            tax_mod.tenant = make(turnover)
            r = client.get(f"/v1/shops/{SHOP}/tax/vat")
            _assert(r.status_code == 200 and r.json()["above_threshold"] is over,
                    f"{turnover}: {r.status_code} {r.text[:160]}")
    finally:
        tax_mod.tenant = saved
check("The VAT monitor counts a seller over the threshold only above £90,000", vat_threshold_is_more_than)


# --- recordSettlementInvoice stores the whole invoice, and getSettlement returns it (7 Oct 2026)
def settlement_invoice():
    SID = UUID("33333333-3333-4333-8333-333333333333")
    cols = ["id","tiktok_statement_id","tiktok_payment_id","settlement_reference",
            "statement_time","activity_date","paid_at","payment_status","currency",
            "statement_amount_minor","payable_amount_minor","total_reserve_amount_minor",
            "tiktok_invoice_number"]
    row = (SID, "202608A-0002", None, None, NOW, date(2026,8,15), None, "PAID", "GBP",
           14750, 13750, -1000, "INV-1")
    sent = []
    class C(Conn):
        def execute(self, sql, args=None):
            flat = " ".join(sql.split())
            if flat.startswith(("insert into tiktok_invoices", "update tiktok_invoices")):
                sent.append((flat[:30], args))
            return super().execute(sql, args)
    def make(found=True):
        import contextlib
        @contextlib.contextmanager
        def fake(_a):
            yield C([("update settlements set", Result(cols, [row] if found else [])),
                     ("update tiktok_invoices", Result([], [])),
                     ("insert into tiktok_invoices", Result([], []))])
        return fake
    gbp = lambda n: {"amount_minor": n, "currency": "GBP"}
    url = f"/v1/shops/{SHOP}/settlements/{SID}/invoice"
    full = {"invoice_number": "INV-1", "invoice_type": "Platform Service Fee",
            "issued_on": "2026-09-01", "period_start": "2026-08-01", "period_end": "2026-08-31",
            "net": gbp(1000), "vat": gbp(200), "gross": gbp(1200)}

    settlements.tenant = make()
    r = client.put(url, json={"invoice_number": "INV-1"})
    _assert(r.status_code == 200 and not sent, f"number only writes no invoice: {r.text[:200]} {sent}")

    r = client.put(url, json=full)
    _assert(r.status_code == 200, r.text[:300])
    _assert([x[0].split()[0] for x in sent] == ["update", "insert"], sent)
    ins = sent[-1][1]
    _assert(ins[1] == "INV-1" and ins[2] == "Platform Service Fee" and ins[6:9] == (1000, 200, 1200)
            and ins[10] == str(SID), ins)

    for bad, why in ((dict(full, gross=gbp(1300)), "gross not net plus VAT"),
                     ({"invoice_number": "INV-1", "gross": gbp(1200)}, "partial invoice"),
                     (dict(full, vat={"amount_minor": 200, "currency": "EUR"}), "wrong currency"),
                     (dict(full, period_start="2026-09-01", period_end="2026-08-01"), "period backwards")):
        sent.clear()
        r = client.put(url, json=bad)
        _assert(r.status_code == 422 and not sent, f"{why}: {r.status_code} {r.text[:160]}")

    settlements.tenant = make(found=False)
    _assert(client.put(url, json=full).status_code == 404, "another shop's settlement")

    dcols = cols + ["net_sales_minor", "fee_minor", "shipping_cost_minor", "adjustment_minor"]
    settlements.tenant = with_conn(settlements, [
        ("from settlements where", Result(dcols, [row + (16000, -1250, 0, 0)])),
        ("from settlement_reconciliation", Result(["a","b","c","d"], [(1, 14750, 1200, 0)])),
        ("from tiktok_invoices", Result(["n","t","i","ps","pe","net","vat","g","c"], [
            ("INV-1", "Platform Service Fee", date(2026,9,1), date(2026,8,1), date(2026,8,31),
             1000, 200, 1200, "GBP")])),
        ("from ledger_entries le", Result(["id","t","s"], [])),
    ])
    r = client.get(f"/v1/shops/{SHOP}/settlements/{SID}")
    _assert(r.status_code == 200, r.text[:300])
    b = r.json()
    _assert(b["invoice"]["invoice_number"] == "INV-1" and b["invoice"]["gross"]["amount_minor"] == 1200
            and b["reconciliation"]["invoiced_gross"]["amount_minor"] == 1200, b)
check("recordSettlementInvoice stores a whole, checked invoice and getSettlement returns it", settlement_invoice)


print()
if failures:
    print(f"{len(failures)} failure(s)")
    sys.exit(1)
print("every handler executed and returned what it promised")
