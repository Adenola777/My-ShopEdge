/**
 * Overview, the first screen after setting up and after every sign-in. Rebuilt on 10 October
 * 2026 to the owner's brief, section 11 (A36 step 5), from what was S6 Today.
 *
 * Top to bottom: the title and subtitle; the period (today, this month, last month) and the
 * basis, with the export and the time of the last update; one primary answer for the period;
 * the full calculation under "Where the money went", every line opening its records; and
 * "What needs your attention", at most five items, which the service caps.
 *
 * The primary answer follows the cost coverage of the period, as the brief sets out. With
 * every product costed it is gross profit after returns and the margin, keeping A8's label
 * and its "before your own running costs and your tax". With some costs missing it is gross
 * profit so far with the coverage sentence (A36.1 item 6). With none, net proceeds and the
 * brief's definition. Every figure is served by `getMoney` or `getToday` (A29.1).
 *
 * What TikTok has paid and still owes, the Shop Money card until this step, moved to
 * Reconcile, so the screen carries one answer rather than competing cards. Today's hero,
 * which counted the day only, gave way to the period switch, whose Today shows the same day.
 *
 * The order count, A16.3, added 9 October 2026. It shows only when `order_usage.state` is
 * `approaching` (80 per cent) or `passed` (100 per cent), and names the larger plan. The
 * count is the account's across every shop, because the plan is the account's. Its link goes
 * to Profile and plan, which shows the plan, because no screen and no operation in this
 * repository changes a running plan: /billing tells a seller with a live plan that there is
 * nothing to choose, and updateSubscription only stops or restores renewal. So the card names
 * the larger plan and does not claim the seller can move to it here.
 */

import Link from "next/link";
import { changePlanHref } from "@/lib/upgrade";
import { api, fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";
import { MoneySections } from "@/components/MoneySections";
import {
  coverageSentence,
  BEFORE_OVERHEADS, CONFIDENCE, CONFIDENCE_MEANING, SEVERITY_TONE, chipClass,
  formatMargin,
} from "@/lib/terms";

export const metadata = { title: "Overview" };

/** @type {Record<string, string>} */
const SEVERITY_WORD = { critical: "Act now", warning: "Check", info: "Note" };

/** @param {number} n */
function orders(n) {
  return `${n.toLocaleString("en-GB")} ${n === 1 ? "order" : "orders"}`;
}

/** What the next plan adds besides orders, in the pricing document's words (10 October 2026). */
/** @type {Record<string, string>} */
const NEXT_BENEFIT = { growth: "product-profit tools", pro: "scheduled exports" };

/**
 * A16.3's card, or nothing below 80 per cent.
 *
 * @param {{ usage: import("@/lib/api-types").components["schemas"]["OrderUsage"] | null | undefined, shopId: string }} props
 */
function OrderUsageCard({ usage, shopId }) {
  if (!usage || (usage.state !== "approaching" && usage.state !== "passed")) return null;
  const { order_count: count, order_limit: limit, plan_name: plan, larger_plan: larger } = usage;
  const ends = formatDate(usage.period_end);
  const passed = usage.state === "passed";
  return (
    <div className={passed ? "note note--warn" : "card"} role="status" data-testid="order-usage">
      <h2>{passed ? `This account has ${count === limit ? "reached" : "passed"} its plan's order limit` : "Orders this billing period"}</h2>
      <p>
        {!passed
          ? `The shops on this account have taken ${count.toLocaleString("en-GB")} of the ${orders(limit)} the ${plan} plan covers in the billing period that ends on ${ends}.`
          : count === limit
            ? `The shops on this account have taken ${orders(count)} in the billing period that ends on ${ends}, which is the ${plan} plan's limit.`
            : `The shops on this account have taken ${orders(count)} in the billing period that ends on ${ends}, which is more than the ${limit.toLocaleString("en-GB")} the ${plan} plan covers.`}
        {" "}Cancelled orders count too.
      </p>
      <p>
        Nothing stops at the limit. MyShopEdge keeps reading your orders, and your figures and
        exports carry on as before.{" "}
        {larger
          ? `The ${larger.name} plan covers up to ${orders(larger.order_limit)} a month.`
          : `The ${plan} plan is the largest MyShopEdge offers.`}
      </p>
      {larger ? (
        <p data-testid="order-usage-next">
          Choose {larger.name} when you are ready for more order capacity
          and {NEXT_BENEFIT[larger.slug] ?? "more of MyShopEdge"}.{" "}
          <Link href={changePlanHref(larger.slug, `/shops/${shopId}/today`)} data-testid="order-usage-choose">
            Choose {larger.name}
          </Link>
        </p>
      ) : null}
      <p className="card__foot">
        <Link href={`/shops/${shopId}/settings/profile`} data-testid="order-usage-plan">See your plan</Link>
      </p>
    </div>
  );
}

/**
 * The first and last day of the month before the one that starts on `from`, as ISO dates.
 * `from` is the service's own first day of this month, so no date here comes from the
 * browser's clock (A29.9).
 *
 * @param {string} from
 */
function monthBefore(from) {
  const y = Number(from.slice(0, 4));
  const m = Number(from.slice(5, 7));
  const start = new Date(Date.UTC(y, m - 2, 1));
  const end = new Date(Date.UTC(y, m - 1, 0));
  return { from: start.toISOString().slice(0, 10), to: end.toISOString().slice(0, 10) };
}

/** @type {Record<string, string>} */
const PERIOD_WORD = { today: "Today", month: "This month", last_month: "Last month" };

/**
 * @param {{
 *   params: Promise<{ shopId: string }>,
 *   searchParams: Promise<Record<string, string>>,
 * }} props
 */
export default async function TodayPage({ params, searchParams }) {
  const { shopId } = await params;
  const query = await searchParams;
  const basis = query.basis === "cash" ? "cash" : "sales";
  const periodKey = query.period === "today" || query.period === "last_month" ? query.period : "month";

  const [result, shops, thisMonth] = await Promise.all([
    fetchShop(shopId, "/today"),
    api("/shops", { cache: "no-store" }),
    fetchShop(shopId, "/money", { basis }),
  ]);
  const problem = apiProblem(result, { what: "your overview" })
    ?? apiProblem(thisMonth, { what: "your money figures" });
  if (problem) return problem;

  // "This month" is the service's default period. Today and last month are worked out from
  // its dates and asked for again.
  let money = thisMonth;
  if (periodKey !== "month") {
    const p = /** @type {{ from: string, to: string }} */ (thisMonth.data.period);
    const range = periodKey === "today" ? { from: p.to, to: p.to } : monthBefore(p.from);
    money = await fetchShop(shopId, "/money", { basis, ...range });
    const again = apiProblem(money, { what: "your money figures" });
    if (again) return again;
  }

  /** @type {import("@/lib/api-types").components["schemas"]["TodayView"]} */
  const t = result.data;
  /** @type {import("@/lib/api-types").components["schemas"]["MoneyView"]} */
  const m = money.data;
  const period = /** @type {{ from: string, to: string }} */ (m.period);
  const shop = shops.ok ? (shops.data?.shops ?? []).find((/** @type {any} */ s) => s.id === shopId) : null;
  const status = t.freshness?.status;
  const [confidence, confidenceTone] = CONFIDENCE[m.confidence] ?? [m.confidence, "quiet"];
  const base = `/shops/${shopId}/today`;
  /** @param {Record<string, string>} q */
  const href = (q) => `${base}${Object.keys(q).length ? `?${new URLSearchParams(q)}` : ""}`;
  /** @type {Record<string, string>} */
  const withBasis = basis === "cash" ? { basis } : {};
  /** @type {Record<string, string>} */
  const withPeriod = periodKey === "month" ? {} : { period: periodKey };
  const soFar = m.totals?.gross_profit_so_far;
  const attention = t.needs_you;

  return (
    <section>
      <header className="page-head">
        {/* Named Overview, with this subtitle, from the owner's brief approved 10 October 2026. */}
        <h1>Overview</h1>
        <p>A clear picture of what your TikTok Shop has left you.</p>
        {shop?.shop_name && <p className="muted">{shop.shop_name}</p>}
      </header>

      {/* Only `stale` raises the banner. `getting_old` starts six hours after a read, and the
          daily read leaves a shop in that state for most of every day, so a banner then would
          stop meaning anything (copy audit 8 October, finding 20). */}
      {status === "stale" && (
        <div className="note note--warn" role="status">
          <p>
            {t.freshness?.last_synced_at
              ? `MyShopEdge last brought these figures up to date ${formatDate(t.freshness.last_synced_at, { time: true })}, more than a day ago, so they may not be current.`
              : "Your shop has not been brought up to date yet, so these figures are not complete."}
          </p>
        </div>
      )}

      {/* The brief's controls: the period, the basis, the export and when the figures were
          last brought up to date. The daily read cannot be started from here, so no refresh
          is offered. */}
      <nav className="switch" aria-label="Period">
        {["today", "month", "last_month"].map((k) => (
          <Link key={k} href={href({ ...withBasis, ...(k === "month" ? {} : { period: k }) })}
                aria-current={periodKey === k ? "true" : undefined}>
            {PERIOD_WORD[k]}
          </Link>
        ))}
      </nav>
      <nav className="switch" aria-label="Basis">
        <Link href={href(withPeriod)} aria-current={basis === "sales" ? "true" : undefined}>Sales basis</Link>
        <Link href={href({ ...withPeriod, basis: "cash" })} aria-current={basis === "cash" ? "true" : undefined}>Cash basis</Link>
      </nav>
      <p className="rows__sub" data-testid="overview-period">
        {periodKey === "today" ? `Today, ${formatDate(period.to)}` : `${formatDate(period.from)} to ${formatDate(period.to)}`},{" "}
        {basis === "sales" ? "counted on the day of each sale" : "counted on the day TikTok settled it"}.
        {t.freshness?.last_synced_at ? ` Last updated ${formatDate(t.freshness.last_synced_at, { time: true })}.` : ""}{" "}
        <Link href={`/shops/${shopId}/money/export`} data-testid="overview-export">Export</Link>
      </p>

      <div className="stack">
        <OrderUsageCard usage={t.order_usage} shopId={shopId} />

        {/* One primary answer, chosen by how much of the period has a cost (brief, section 11). */}
        <div className="card hero" data-testid="overview-primary">
          {m.kept ? (
            <>
              <p className="hero__label">
                Gross profit after returns{" "}
                <span className={chipClass(confidenceTone)} title={CONFIDENCE_MEANING[m.confidence]}>{confidence}</span>
              </p>
              <p className="hero__value"><Figure amount={m.kept} /></p>
              {formatMargin(m.totals?.gross_margin_after_returns) && (
                <p className="hero__line" data-testid="overview-margin">Gross margin after returns {formatMargin(m.totals.gross_margin_after_returns)}</p>
              )}
              <p className="hero__line">{BEFORE_OVERHEADS}</p>
              <p className="hero__line"><Link href={`/shops/${shopId}/products`}>View product performance</Link></p>
            </>
          ) : soFar ? (
            <>
              <p className="hero__label">
                Gross profit so far{" "}
                <span className={chipClass(confidenceTone)} title={CONFIDENCE_MEANING[m.confidence]}>{confidence}</span>
              </p>
              <p className="hero__value"><Figure amount={soFar} /></p>
              {coverageSentence(m.coverage) && <p className="hero__line" data-testid="overview-coverage">{coverageSentence(m.coverage)}</p>}
              <p className="hero__line"><Link href={`/shops/${shopId}/setup/costs/manual`}>Review missing costs</Link></p>
            </>
          ) : (
            <>
              <p className="hero__label">
                Net proceeds{" "}
                <span className={chipClass(confidenceTone)} title={CONFIDENCE_MEANING[m.confidence]}>{confidence}</span>
              </p>
              <p className="hero__value"><Figure amount={m.totals?.net_proceeds} /></p>
              <p className="hero__line">What remains after TikTok Shop deductions, before product costs.</p>
              {m.kept_reason !== "no_sales" && (
                <p className="hero__line"><Link href={`/shops/${shopId}/setup/costs`}>Add product costs</Link></p>
              )}
            </>
          )}
        </div>

        <h2>Where the money went</h2>
        {m.sections.length === 0 ? (
          <div className="card" data-testid="overview-empty">
            <p className="muted">
              {basis === "cash"
                ? "MyShopEdge holds no money that TikTok settled in this period."
                : "MyShopEdge holds no sales, fees, refunds or payouts for this period."}
            </p>
          </div>
        ) : (
          <MoneySections m={m} shopId={shopId} basis={basis} />
        )}

        <div className="card" data-testid="overview-attention">
          <h2>What needs your attention</h2>
          {attention.length === 0 ? (
            <>
              <h3>You are up to date</h3>
              <p className="muted">There is nothing that needs your attention right now.</p>
            </>
          ) : (
            <ul className="rows">
              {attention.map((n) => (
                <li key={n.type}>
                  <span>
                    {n.href
                      ? <Link href={n.href}>{n.label ?? "Something needs your attention"}</Link>
                      : (n.label ?? "Something needs your attention")}
                    {n.amount_at_stake && (
                      <span className="rows__sub"> <Figure amount={n.amount_at_stake} /> is affected.</span>
                    )}
                  </span>
                  <span className={chipClass(SEVERITY_TONE[n.severity] ?? "quiet")}>
                    {SEVERITY_WORD[n.severity] ?? n.severity}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
