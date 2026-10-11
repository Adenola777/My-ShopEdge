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
  CONFIDENCE, CONFIDENCE_MEANING, SEVERITY_TONE, chipClass,
  formatMargin,
} from "@/lib/terms";

export const metadata = { title: "Overview" };

/** @type {Record<string, string>} */
const SEVERITY_WORD = { critical: "Act now", warning: "Check", info: "Note" };

/**
 * What upgrading from each plan adds, in the owner's words (A38, 11 October 2026).
 * @type {Record<string, string>}
 */
const NEXT_BENEFIT = {
  starter: "Upgrade to Starter for 500 orders per month and full product profit.",
  growth: "Upgrade to Growth for 1,000 orders per month, exports and multi-shop support.",
  pro: "Upgrade to Pro for unlimited orders and up to 10 TikTok Shops.",
};

/**
 * The monthly order limit at 80 and 100 per cent (A38), or nothing below 80 per cent. Amber
 * and calm, never red, because reaching a limit is not a fault.
 *
 * @param {{ usage: import("@/lib/api-types").components["schemas"]["OrderUsage"] | null | undefined, shopId: string }} props
 */
function OrderUsageCard({ usage, shopId }) {
  if (!usage || (usage.state !== "approaching" && usage.state !== "passed")) return null;
  const { order_count: count, order_limit: limit, plan_name: plan, larger_plan: larger } = usage;
  const passed = usage.state === "passed";
  return (
    <div className="note note--warn order-usage" role="status" data-testid="order-usage">
      <h2>{passed ? "Monthly order limit reached" : "You are close to your monthly order limit"}</h2>
      <p>
        {passed
          ? `Your ${plan} plan includes up to ${limit.toLocaleString("en-GB")} orders per month. Your existing data remains available, but new orders will not sync until your billing period resets or you upgrade.`
          : `You have processed ${count.toLocaleString("en-GB")} of ${limit.toLocaleString("en-GB")} orders this month.`}
      </p>
      {larger && <p data-testid="order-usage-next">{NEXT_BENEFIT[larger.slug]}</p>}
      <p className="upload__actions">
        {larger && (
          <Link className="btn btn--primary btn--small" href={changePlanHref(larger.slug)} data-testid="order-usage-choose">
            Upgrade to {larger.name}
          </Link>
        )}
        <Link className="btn btn--quiet btn--small" href={`/shops/${shopId}/settings/profile`} data-testid="order-usage-plan">View usage</Link>
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
  // The period and basis, in a few words, under the main figure (A37 phase 2).
  const when = periodKey === "today" ? `Today, ${formatDate(period.to)}` : `${formatDate(period.from)} to ${formatDate(period.to)}`;
  const basisWord = basis === "sales" ? "Sales basis" : "Cash basis";
  const margin = formatMargin(m.totals?.gross_margin_after_returns);

  // A37 phase 2, the owner's ruling of 11 October 2026: the Overview is the first screen a
  // seller sees, so it holds the answer and nothing that explains it. The definitions are in
  // the glossary, and every line opens its records. Top to bottom: the title, one row of
  // controls, the main figure, the statement, and what needs attention.
  return (
    <section className="overview">
      <header className="page-head page-head--row">
        <div>
          <h1>Overview</h1>
          {shop?.shop_name && <p>{shop.shop_name}</p>}
        </div>
        <div className="page-head__actions">
          <Link className="btn btn--quiet btn--small" href={`/shops/${shopId}/money/export`} data-testid="overview-export">Export</Link>
        </div>
      </header>

      {/* Only `stale` raises the banner. `getting_old` starts six hours after a read, and the
          daily read leaves a shop in that state for most of every day, so a banner then would
          stop meaning anything (copy audit 8 October, finding 20). */}
      {status === "stale" && (
        <p className="note note--warn" role="status">
          {t.freshness?.last_synced_at
            ? `Last updated ${formatDate(t.freshness.last_synced_at, { time: true })}, over a day ago.`
            : "Not updated yet. Figures are incomplete."}
        </p>
      )}

      <div className="toolbar">
        <nav className="switch switch--compact" aria-label="Period">
          {["today", "month", "last_month"].map((k) => (
            <Link key={k} href={href({ ...withBasis, ...(k === "month" ? {} : { period: k }) })}
                  aria-current={periodKey === k ? "true" : undefined}>
              {PERIOD_WORD[k]}
            </Link>
          ))}
        </nav>
        <nav className="switch switch--compact" aria-label="Basis">
          <Link href={href(withPeriod)} aria-current={basis === "sales" ? "true" : undefined}>Sales basis</Link>
          <Link href={href({ ...withPeriod, basis: "cash" })} aria-current={basis === "cash" ? "true" : undefined}>Cash basis</Link>
        </nav>
      </div>

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
            <p className="hero__meta" data-testid="overview-period">
              {margin && <span data-testid="overview-margin"><strong>{margin}</strong> margin</span>}
              <span>{when}</span>
              <span>{basisWord}</span>
            </p>
            <p className="hero__action"><Link href={`/shops/${shopId}/products`}>View product performance</Link></p>
          </>
        ) : soFar ? (
          <>
            <p className="hero__label">
              Gross profit so far{" "}
              <span className={chipClass(confidenceTone)} title={CONFIDENCE_MEANING[m.confidence]}>{confidence}</span>
            </p>
            <p className="hero__value"><Figure amount={soFar} /></p>
            {coverageSentence(m.coverage) && <p className="hero__line" data-testid="overview-coverage">{coverageSentence(m.coverage)}</p>}
            <p className="hero__meta" data-testid="overview-period"><span>{when}</span><span>{basisWord}</span></p>
            <p className="hero__action"><Link href={`/shops/${shopId}/setup/costs/manual`}>Review missing costs</Link></p>
          </>
        ) : (
          <>
            <p className="hero__label">
              Net proceeds{" "}
              <span className={chipClass(confidenceTone)} title={CONFIDENCE_MEANING[m.confidence]}>{confidence}</span>
            </p>
            <p className="hero__value"><Figure amount={m.totals?.net_proceeds} /></p>
            <p className="hero__line">After TikTok deductions, before product costs.</p>
            <p className="hero__meta" data-testid="overview-period"><span>{when}</span><span>{basisWord}</span></p>
            {m.kept_reason !== "no_sales" && (
              <p className="hero__action"><Link href={`/shops/${shopId}/setup/costs`}>Add product costs</Link></p>
            )}
          </>
        )}
      </div>

      <h2 className="overview__heading">Where the money went</h2>
      {m.sections.length === 0 ? (
        <div className="card" data-testid="overview-empty">
          <p className="muted">Nothing recorded in this period.</p>
        </div>
      ) : (
        // What TikTok paid out is left to Reconcile, so the statement ends at gross profit.
        <MoneySections m={m} shopId={shopId} basis={basis} omit={["payout"]} />
      )}

      <h2 className="overview__heading">What needs your attention</h2>
      <div className="card" data-testid="overview-attention">
        {attention.length === 0 ? (
          <p className="overview__clear"><span aria-hidden="true">{"\u2713"}</span> You are up to date.</p>
        ) : (
          <ul className="rows">
            {attention.map((n) => (
              <li key={n.type}>
                <span>
                  {n.href
                    ? <Link className="rowlink rowlink--quiet" href={n.href}>{n.label ?? "Something needs your attention"}</Link>
                    : (n.label ?? "Something needs your attention")}
                  {n.amount_at_stake && (
                    <span className="rows__sub" style={{ display: "block" }}><Figure amount={n.amount_at_stake} /> affected</span>
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
    </section>
  );
}
