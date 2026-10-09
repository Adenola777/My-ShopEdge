/**
 * S6 Today, drawn to wireframe sheet 04 (redrawn 24 September after the design audit).
 *
 * The wireframe, top to bottom: the title with the shop's name under it; the hero; this
 * month's two figures side by side; Shop Money; the VAT line; Needs you. Each card carries a
 * title and one line on why it matters (WFW 1.1).
 *
 * What differs from the sheet, and the ruling that made it differ.
 * - "You keep" is Gross profit after returns and "Left after TikTok" is Net proceeds (A8),
 *   and the sentence "before your own running costs and your tax" goes with the figure.
 * - The VAT line is gone, because VAT is out of scope (A29.8).
 * - Shop Money states return postage on its own line so Paid out reconciles (A29.7). Paid
 *   out is not drawn as a total, because it equals the lines above only when nothing is
 *   awaiting settlement (copy audit 8 October, finding 4).
 * - The hero's second line on the sheet ("From £X of sales across N orders") needs the
 *   day's sales and order count, which TodayView does not carry. Phase 3 of the audit adds
 *   them to the contract first. Until then the line is the before-overheads sentence.
 *
 * Every figure is served by `getToday` and rendered as it arrives (A29.1). Freshness is in
 * the top bar; this screen adds a banner only when the figures are not current (WFW 6).
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
import { api, fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";
import {
  AWAITING, BEFORE_OVERHEADS, CONFIDENCE, CONFIDENCE_MEANING, HERO_LABEL, SEVERITY_TONE, chipClass,
  keptReason,
} from "@/lib/terms";

export const metadata = { title: "Today" };

/** @type {Record<string, string>} */
const SEVERITY_WORD = { critical: "Act now", warning: "Check", info: "Note" };

/** @param {number} n */
function orders(n) {
  return `${n.toLocaleString("en-GB")} ${n === 1 ? "order" : "orders"}`;
}

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
      <p className="card__foot">
        <Link href={`/shops/${shopId}/settings/profile`} data-testid="order-usage-plan">See your plan</Link>
      </p>
    </div>
  );
}

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function TodayPage({ params }) {
  const { shopId } = await params;
  const [result, shops] = await Promise.all([
    fetchShop(shopId, "/today"),
    api("/shops", { cache: "no-store" }),
  ]);
  const problem = apiProblem(result, { what: "today's figures" });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["TodayView"]} */
  const t = result.data;
  const shop = shops.ok ? (shops.data?.shops ?? []).find((/** @type {any} */ s) => s.id === shopId) : null;
  const [confidence, confidenceTone] = CONFIDENCE[t.hero.confidence] ?? [t.hero.confidence, "quiet"];
  const isProfit = t.hero.label === "gross_profit_after_returns";
  const status = t.freshness?.status;
  const sm = t.shop_money;
  const awaiting = sm.awaiting_breakdown ?? [];

  return (
    <section>
      <header className="page-head">
        <h1>Today</h1>
        {shop?.shop_name && <p>{shop.shop_name}</p>}
      </header>

      {(status === "stale" || status === "getting_old") && (
        <div className="note note--warn" role="status">
          <p>
            {t.freshness?.last_synced_at
              ? `MyShopEdge last brought these figures up to date ${formatDate(t.freshness.last_synced_at, { time: true })}, ${status === "stale" ? "more than a day ago" : "more than six hours ago"}, so they may not be current.`
              : "Your shop has not been brought up to date yet, so these figures are not complete."}
          </p>
        </div>
      )}

      <div className="stack">
        <OrderUsageCard usage={t.order_usage} shopId={shopId} />

        <div className="card hero">
          <p className="hero__label">
            {HERO_LABEL[t.hero.label] ?? t.hero.label} today{" "}
            <span className={chipClass(confidenceTone)} title={CONFIDENCE_MEANING[t.hero.confidence]}>{confidence}</span>
          </p>
          <p className="hero__value"><Figure amount={t.hero.value} /></p>
          {isProfit ? (
            <p className="hero__line">{BEFORE_OVERHEADS}</p>
          ) : (
            <p className="hero__line">
              This is net proceeds, because not every product sold today has a cost price yet.{" "}
              <Link href={`/shops/${shopId}/products`}>Add costs</Link>
            </p>
          )}
        </div>

        <div className="pair">
          <div className="card">
            <p className="stat__value"><Figure amount={t.month.gross} /></p>
            <p className="stat__label">Gross sales this month</p>
          </div>
          <div className="card">
            <p className="stat__value"><Figure amount={t.month.kept} /></p>
            <p className="stat__label">Gross profit after returns this month</p>
            {!t.month.kept && t.month.kept_reason && (
              <p className="rows__sub">{keptReason(t.month.kept_reason)}</p>
            )}
          </div>
        </div>

        <div className="card">
          <h2>Shop Money</h2>
          <p className="card__why">
            This card covers every sale MyShopEdge holds for this shop. It shows what TikTok has
            paid you, and what it still owes you.
          </p>
          <ul className="rows">
            <li><span>Net proceeds, all time</span><Figure amount={sm.generated} /></li>
            {sm.return_postage && sm.return_postage.amount_minor !== 0 && (
              <li><span>Return shipping TikTok deducted</span><Figure amount={sm.return_postage} /></li>
            )}
            <li><span>Paid out</span><Figure amount={sm.paid_out} /></li>
            <li>
              <span>Awaiting settlement</span>
              <span className="chip chip--warn"><Figure amount={sm.awaiting} /></span>
            </li>
          </ul>
          <p className="rows__sub">
            Paid out and awaiting settlement together make up net proceeds less the return
            shipping TikTok deducted.
          </p>
          {awaiting.length > 0 && (
            <details className="disclose">
              <summary>What is awaiting settlement</summary>
              <ul className="rows">
                {awaiting.map((a) => (
                  <li key={a.status} className="rows__sub">
                    <span>
                      {AWAITING[a.status] ?? "Awaiting settlement"}, {a.orders} {a.orders === 1 ? "order" : "orders"}
                    </span>
                    <Figure amount={a.amount} />
                  </li>
                ))}
              </ul>
            </details>
          )}
          <p className="card__foot">
            <Link href={`/shops/${shopId}/money`}>See where every pound went</Link>
          </p>
        </div>

        <div className="card">
          <h2>Needs your attention</h2>
          <p className="card__why">What is holding your figures back, most urgent first.</p>
          {t.needs_you.length === 0 ? (
            <p className="muted">Nothing needs your attention right now.</p>
          ) : (
            <ul className="rows">
              {t.needs_you.map((n) => (
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
