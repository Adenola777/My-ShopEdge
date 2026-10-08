"""Tax. The profile, the VAT threshold monitor, and the set-aside estimate.

Written by Emergent AI in `Adenola777/MYSHOPEDGE` (commits 91aeed4, 25 September, and
3f1bd43, 27 September 2026) and brought into this repository unchanged on 28 September at
the owner's instruction, after review in `audit/EMERGENT_review_28_september.md`.

Traces TAX-1, TAX-2 and TAX-3. This module monitors a threshold and estimates a set-aside.
It does not prepare or submit a VAT return and it does not account for VAT on a registered
seller's behalf, both of which PRD 6.2 excludes.

The VAT registration threshold is not held in code. It is a reference rule, read from
`reference_rules` with its own `reviewed_at`, because a threshold that a release hard-codes
is one a release has to change. The current value, GBP 90,000 from 1 April 2024, is HMRC's
under the Value Added Tax (Increase of Registration Limits) Order 2024.

The set-aside follows A30.3, ruled 28 September 2026: a simple estimate for a sole trader,
income tax and Class 4 National Insurance on profit to date, at the bands in force, read
from reference rules. A limited company sees no figure. The method is in `_estimate` below
and every number it uses is a reference rule, so no rate or band is written in this file.
**No band is loaded on any branch**, because gov.uk could not be reached to check one, and
until reviewed rules exist the set-aside answers with no amount and says why. A seller who
under-saves on a made-up number has been failed by the product, which is TAX-3's own warning.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from .auth import Account, require_account
from .dates import business_today, now_utc
from .db import tenant, unscoped
from .money import Money, money
from .money_view import calculate
from .problems import Problem
from .shops import require_shop

router = APIRouter(tags=["Tax"])

Structure = Literal["sole_trader", "company", "not_sure"]
Confidence = Literal["confirmed", "estimated", "incomplete"]


class TaxProfileIn(BaseModel):
    business_structure: Structure | None = None
    vat_registered: bool = False
    vat_registered_from: str | None = None


class TaxProfileOut(TaxProfileIn):
    completed: bool
    updated_at: str | None = None


class MonthTurnover(BaseModel):
    month: str
    tiktok_gross: Money
    other_channels_gross: Money


class VatMonitorOut(BaseModel):
    as_of: str
    rolling_twelve_month_turnover: Money
    threshold: Money
    headroom: Money
    above_threshold: bool
    includes_other_channels: bool
    months: list[MonthTurnover]
    rule_key: str
    reviewed_at: str | None = None


class BasisItem(BaseModel):
    label: str
    amount: Money | None = None
    rule_key: str | None = None


class SetAsidePeriod(BaseModel):
    from_: date = Field(serialization_alias="from")
    to: date
    basis: Literal["sales", "cash"]


class SetAsideOut(BaseModel):
    as_of: str
    amount: Money | None = None
    unavailable_reason: Literal["incomplete_costs", "no_tax_profile", "insufficient_history"] | None = None
    confidence: Confidence
    period: SetAsidePeriod | None = None
    basis_of_estimate: list[BasisItem] = []


def _profile_row(account: Account, conn) -> tuple | None:
    return conn.execute(
        "select business_structure, vat_registered, vat_registered_from, updated_at "
        "from tax_profiles where account_id = %s",
        (str(account.id),),
    ).fetchone()


def _profile_out(row: tuple | None) -> TaxProfileOut:
    if row is None:
        return TaxProfileOut(business_structure=None, vat_registered=False,
                             vat_registered_from=None, completed=False, updated_at=None)
    bs, vr, vrf, ua = row
    return TaxProfileOut(
        business_structure=bs,
        vat_registered=vr,
        vat_registered_from=vrf.isoformat() if vrf else None,
        completed=True,
        updated_at=ua.isoformat() if ua else None,
    )


@router.get("/tax-profile", response_model=TaxProfileOut, summary="Read the tax profile")
def get_tax_profile(account: Annotated[Account, Depends(require_account)]) -> TaxProfileOut:
    with tenant(account.id) as conn:
        return _profile_out(_profile_row(account, conn))


@router.put("/tax-profile", response_model=TaxProfileOut, summary="Save the tax profile")
def put_tax_profile(
    body: TaxProfileIn,
    account: Annotated[Account, Depends(require_account)],
) -> TaxProfileOut:
    # A VAT monitor without a registration date cannot say which periods are in scope.
    registered_from: date | None = None
    if body.vat_registered:
        if not body.vat_registered_from:
            raise Problem(422, "vat_date_required", "Tell us the date you registered for VAT.")
        try:
            registered_from = date.fromisoformat(body.vat_registered_from)
        except ValueError as exc:
            raise Problem(422, "vat_date_invalid", "The VAT registration date is not a date.") from exc

    # A full replacement, not a patch. An omitted field is cleared.
    with tenant(account.id) as conn:
        row = conn.execute(
            "insert into tax_profiles "
            "(account_id, business_structure, vat_registered, vat_registered_from, updated_at) "
            "values (%s, %s, %s, %s, now()) "
            "on conflict (account_id) do update set "
            "business_structure = excluded.business_structure, "
            "vat_registered = excluded.vat_registered, "
            "vat_registered_from = excluded.vat_registered_from, "
            "updated_at = now() "
            "returning business_structure, vat_registered, vat_registered_from, updated_at",
            (str(account.id), body.business_structure, body.vat_registered, registered_from),
        ).fetchone()
    return _profile_out(row)


def _twelve_months(today: date) -> list[tuple[int, int]]:
    """The current London month and the eleven before it, oldest first."""
    seq: list[tuple[int, int]] = []
    for i in range(11, -1, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        seq.append((year, month))
    return seq


@router.get("/shops/{shopId}/tax/vat", response_model=VatMonitorOut, summary="VAT threshold monitor")
def get_vat_monitor(
    shopId: Annotated[UUID, Depends(require_shop)],
    account: Annotated[Account, Depends(require_account)],
) -> VatMonitorOut:
    today = business_today()
    seq = _twelve_months(today)
    window_start = date(seq[0][0], seq[0][1], 1)

    with tenant(account.id) as conn:
        gross = dict(conn.execute(
            "select to_char(date_trunc('month', (occurred_at at time zone 'Europe/London')), 'YYYY-MM'), "
            "coalesce(sum(amount_minor), 0) from ledger_entries "
            "where shop_id = %s and category = 'gross_sales' "
            "and (occurred_at at time zone 'Europe/London')::date >= %s group by 1",
            (str(shopId), window_start),
        ).fetchall())
        other = dict(conn.execute(
            "select to_char(month, 'YYYY-MM'), coalesce(sum(gross_minor), 0) "
            "from other_channel_sales where shop_id = %s and month >= %s group by 1",
            (str(shopId), window_start),
        ).fetchall())
        has_other = conn.execute(
            "select exists(select 1 from other_channel_sales where shop_id = %s)",
            (str(shopId),),
        ).fetchone()[0]
        rule = conn.execute(
            "select rule_key, value, reviewed_at from reference_rules "
            "where rule_set = 'vat' and rule_key = 'registration_threshold' "
            "and effective_from <= %s and (effective_to is null or effective_to >= %s) "
            "order by effective_from desc limit 1",
            (today, today),
        ).fetchone()

    if rule is None:
        raise Problem(503, "vat_unconfigured",
                      "The VAT registration threshold has not been loaded yet, so this "
                      "screen cannot say where you stand against it.")
    rule_key, value, reviewed_at = rule
    threshold_minor = int(value["amount_minor"])
    currency = value.get("currency", "GBP")

    months: list[MonthTurnover] = []
    tiktok_total = 0
    other_total = 0
    for year, month in seq:
        key = f"{year:04d}-{month:02d}"
        tg = int(gross.get(key, 0))
        og = int(other.get(key, 0))
        tiktok_total += tg
        other_total += og
        months.append(MonthTurnover(
            month=key,
            tiktok_gross=money(tg, currency),
            other_channels_gross=money(og, currency),
        ))
    turnover = tiktok_total + other_total

    return VatMonitorOut(
        as_of=now_utc().isoformat(),
        rolling_twelve_month_turnover=money(turnover, currency),
        threshold=money(threshold_minor, currency),
        headroom=money(threshold_minor - turnover, currency),
        # gov.uk: register when taxable turnover is "More than £90,000", so equal is not over.
        above_threshold=turnover > threshold_minor,
        includes_other_channels=has_other,
        months=months,
        rule_key=rule_key,
        reviewed_at=reviewed_at.isoformat() if reviewed_at else None,
    )


# --- getTaxSetAside, TAX-3 and A30.3 --------------------------------------------------------
#
# The rules the estimate reads, one row per tax year through `effective_from` and
# `effective_to`, each used only once `reviewed_at` is set. The first two are in rule set
# `income_tax` and the third in `national_insurance`, the two sets the schema's check allows:
#
#   income_tax_personal_allowance  {"amount_minor": int,
#                                   "taper_from_minor": int | null, "taper_ratio": int}
#   income_tax_bands               {"bands": [{"width_minor": int | null, "rate_bp": int}]}
#                                  in order on taxable income; a null width is the last band
#   class4_nic                     {"lower_minor": int, "upper_minor": int,
#                                   "main_rate_bp": int, "upper_rate_bp": int}
#
# Rates are in basis points. The shape is this module's; the values are HMRC's and belong in
# the table with `source_url` naming the gov.uk page they were read from.

SET_ASIDE_RULES = ("income_tax_personal_allowance", "income_tax_bands", "class4_nic")


def _tax_year_start(today: date) -> date:
    """6 April of the UK tax year `today` falls in."""
    start = date(today.year, 4, 6)
    return start if today >= start else date(today.year - 1, 4, 6)


def _pence(amount: int, rate_bp: int) -> int:
    return int((Decimal(amount) * rate_bp / 10000).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _estimate(profit: int, rules: dict) -> tuple[int, int, int]:
    """Income tax and Class 4 on `profit`, all in minor units: (allowance, tax, class 4).

    The allowance is reduced by one for every `taper_ratio` above `taper_from_minor` when
    the rule sets a taper. Bands apply to taxable income in order. Class 4 applies to the
    profit between the lower and upper limits at the main rate, and above the upper limit at
    the upper rate. Nothing else is modelled: no other income, no reliefs, no Class 2.
    """
    profit = max(profit, 0)
    pa_rule = rules["income_tax_personal_allowance"]
    allowance = int(pa_rule["amount_minor"])
    taper_from = pa_rule.get("taper_from_minor")
    if taper_from is not None and profit > taper_from:
        allowance = max(0, allowance - (profit - int(taper_from)) // int(pa_rule.get("taper_ratio", 2)))

    remaining, tax = max(profit - allowance, 0), 0
    for band in rules["income_tax_bands"]["bands"]:
        width = band.get("width_minor")
        part = remaining if width is None else min(remaining, int(width))
        tax += _pence(part, int(band["rate_bp"]))
        remaining -= part
        if remaining <= 0:
            break

    c4 = rules["class4_nic"]
    lower, upper = int(c4["lower_minor"]), int(c4["upper_minor"])
    class4 = _pence(max(min(profit, upper) - lower, 0), int(c4["main_rate_bp"]))
    class4 += _pence(max(profit - upper, 0), int(c4["upper_rate_bp"]))
    return allowance, tax, class4


@router.get("/shops/{shopId}/tax/set-aside", response_model=SetAsideOut, summary="Set-aside estimate")
def get_set_aside(
    shopId: Annotated[UUID, Depends(require_shop)],
    account: Annotated[Account, Depends(require_account)],
) -> SetAsideOut:
    as_of = now_utc().isoformat()
    today = business_today()
    start = _tax_year_start(today)
    period = SetAsidePeriod(from_=start, to=today, basis="sales")
    with tenant(account.id) as conn:
        profile = _profile_row(account, conn)
        if profile is None:
            return SetAsideOut(
                as_of=as_of, amount=None, unavailable_reason="no_tax_profile",
                confidence="incomplete",
                basis_of_estimate=[BasisItem(
                    label="Fill in your tax profile so a set-aside can be estimated.")],
            )
        structure = profile[0]
        if structure == "company":
            return SetAsideOut(
                as_of=as_of, amount=None, confidence="incomplete",
                basis_of_estimate=[BasisItem(
                    label="A limited company pays Corporation Tax on its own profits, so no "
                          "personal set-aside is estimated.")],
            )
        if structure != "sole_trader":
            return SetAsideOut(
                as_of=as_of, amount=None, unavailable_reason="no_tax_profile",
                confidence="incomplete",
                basis_of_estimate=[BasisItem(
                    label="Choose sole trader or limited company in your tax profile so a "
                          "set-aside can be estimated.")],
            )

        rows = conn.execute(
            "select distinct on (rule_key) rule_key, value from reference_rules "
            "where rule_set in ('income_tax', 'national_insurance') and rule_key = any(%s) "
            "and reviewed_at is not null "
            "and effective_from <= %s and (effective_to is null or effective_to >= %s) "
            "order by rule_key, effective_from desc",
            (list(SET_ASIDE_RULES), today, today),
        ).fetchall()
        rules = {k: v for k, v in rows}
        if len(rules) < len(SET_ASIDE_RULES):
            return SetAsideOut(
                as_of=as_of, amount=None, confidence="incomplete", period=period,
                basis_of_estimate=[BasisItem(
                    label="The income tax and National Insurance rates for this tax year are "
                          "not loaded yet, so no amount can be produced.")],
            )
        view = calculate(conn, shopId, start, today, "sales")

    currency = view.totals.net_sales.currency if view.totals.net_sales else "GBP"
    if view.kept is None and view.kept_reason == "incomplete_costs":
        return SetAsideOut(
            as_of=as_of, amount=None, unavailable_reason="incomplete_costs",
            confidence="incomplete", period=period,
            basis_of_estimate=[BasisItem(
                label="Some products you sold have no cost, so your profit is not known.")],
        )
    profit = view.kept.amount_minor if view.kept is not None else 0
    allowance, tax, class4 = _estimate(profit, rules)
    return SetAsideOut(
        as_of=as_of, amount=money(tax + class4, currency),
        # Always an estimate: the tax year is not over, and only this shop's profit is known.
        confidence="estimated", period=period,
        basis_of_estimate=[
            BasisItem(label="Profit so far this tax year, by sale date, before overheads",
                      amount=money(profit, currency)),
            BasisItem(label="Personal Allowance", amount=money(allowance, currency),
                      rule_key="income_tax_personal_allowance"),
            BasisItem(label="Income Tax", amount=money(tax, currency), rule_key="income_tax_bands"),
            BasisItem(label="Class 4 National Insurance", amount=money(class4, currency),
                      rule_key="class4_nic"),
            BasisItem(label="This assumes the shop is your only income and leaves out your "
                            "overheads, other income and reliefs. It is not tax advice."),
        ],
    )


# --- getTaxDates, TAX-4 --------------------------------------------------------------------
#
# The key Self Assessment dates for a UK tax year, each computed from a reference rule so it
# carries the date the rule was last reviewed and its source. A tax year Y runs 6 April Y to
# 5 April Y+1, and each rule's value gives the month, day and how many years after Y the
# date falls. A date whose rule is not configured is left out rather than guessed, so an
# empty list is an honest answer that the rules are not loaded rather than a wrong one.


class TaxDate(BaseModel):
    label: str
    date: str
    rule_key: str
    reviewed_at: str | None = None
    source_url: str | None = None


class TaxDatesOut(BaseModel):
    tax_year: int
    dates: list[TaxDate]


@router.get("/tax/dates", response_model=TaxDatesOut, summary="Quarterly and payment dates")
def get_tax_dates(
    account: Annotated[Account, Depends(require_account)],
    tax_year: Annotated[int | None, Query(ge=2020, le=2100)] = None,
) -> TaxDatesOut:
    today = business_today()
    # The UK tax year that is current today: it begins on 6 April. Before 6 April the
    # current year started in the previous calendar year.
    year = tax_year if tax_year is not None else (
        today.year if (today.month, today.day) >= (4, 6) else today.year - 1
    )
    ref_date = date(year, 4, 6)
    with unscoped() as conn:
        rows = conn.execute(
            "select rule_key, value, reviewed_at, source_url from reference_rules "
            "where rule_set = 'income_tax' and rule_key like 'date.%%' "
            "and effective_from <= %s and (effective_to is null or effective_to >= %s) "
            "order by rule_key",
            (ref_date, ref_date),
        ).fetchall()

    dates: list[TaxDate] = []
    for rule_key, value, reviewed_at, source_url in rows:
        v = value if isinstance(value, dict) else {}
        try:
            when = date(year + int(v["year_offset"]), int(v["month"]), int(v["day"]))
        except (KeyError, ValueError, TypeError):
            continue
        dates.append(TaxDate(
            label=str(v.get("label", rule_key)),
            date=when.isoformat(),
            rule_key=rule_key,
            reviewed_at=reviewed_at.isoformat() if reviewed_at else None,
            source_url=source_url,
        ))
    dates.sort(key=lambda d: d.date)
    return TaxDatesOut(tax_year=year, dates=dates)


# --- quarterlyCheck, TAX-5 -----------------------------------------------------------------
#
# A comparison, not advice. The seller supplies their prior-year gross income and it is
# compared with the income thresholds in force for the year. `above_threshold` states a fact
# about a number and nothing more, which is why the response carries no recommendation field.


class QuarterlyCheckIn(BaseModel):
    prior_year_gross: Money
    tax_year: int | None = None


class ThresholdComparison(BaseModel):
    rule_key: str
    label: str
    threshold: Money
    above_threshold: bool
    headroom: Money | None = None
    reviewed_at: str | None = None


class QuarterlyCheckOut(BaseModel):
    tax_year: int
    prior_year_gross: Money
    thresholds: list[ThresholdComparison]
    checked_at: str


@router.post("/tax/quarterly-check", response_model=QuarterlyCheckOut,
             summary="Compare prior-year gross income with the thresholds")
def quarterly_check(
    body: QuarterlyCheckIn,
    account: Annotated[Account, Depends(require_account)],
) -> QuarterlyCheckOut:
    if body.prior_year_gross.amount_minor < 0:
        raise Problem(422, "validation_failed", "Prior-year gross income cannot be negative.")
    today = business_today()
    year = body.tax_year if body.tax_year is not None else (
        today.year if (today.month, today.day) >= (4, 6) else today.year - 1
    )
    ref_date = date(year, 4, 6)
    gross = body.prior_year_gross.amount_minor
    currency = body.prior_year_gross.currency

    with unscoped() as conn:
        rows = conn.execute(
            "select rule_key, value, reviewed_at, rule_set from reference_rules "
            "where rule_set in ('mtd', 'income_tax', 'national_insurance') "
            "and rule_key like 'threshold.%%' "
            "and effective_from <= %s and (effective_to is null or effective_to >= %s) "
            "order by rule_set, rule_key",
            (ref_date, ref_date),
        ).fetchall()

    thresholds: list[ThresholdComparison] = []
    for rule_key, value, reviewed_at, _rule_set in rows:
        v = value if isinstance(value, dict) else {}
        if "amount_minor" not in v:
            continue
        amount = int(v["amount_minor"])
        thresholds.append(ThresholdComparison(
            rule_key=rule_key,
            label=str(v.get("label", rule_key)),
            threshold=money(amount, v.get("currency", currency)),
            above_threshold=gross >= amount,
            headroom=money(amount - gross, v.get("currency", currency)),
            reviewed_at=reviewed_at.isoformat() if reviewed_at else None,
        ))

    return QuarterlyCheckOut(
        tax_year=year,
        prior_year_gross=body.prior_year_gross,
        thresholds=thresholds,
        checked_at=now_utc().isoformat(),
    )
