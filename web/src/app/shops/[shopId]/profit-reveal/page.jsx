/**
 * The gross profit reveal, the brief's section 9, approved by the owner under A36 (step 2, 10
 * October 2026). A seller reaches it after saving product costs. It covers the last 30 London
 * days, like the first reconciliation.
 *
 * Every figure is the service's (`getMoney`). With every cost known it shows gross profit and
 * margin. With some missing it shows gross profit so far, over the costed products only, and
 * the brief's coverage sentence by share of sales value (A36 step 3).
 */

import Link from "next/link";
import { fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";
import { BEFORE_OVERHEADS, coverageSentence, formatMargin } from "@/lib/terms";

export const metadata = { title: "Your product profit" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function ProfitRevealPage({ params }) {
  const { shopId } = await params;
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/London" }).format(new Date());
  const start = new Date(`${today}T12:00:00Z`);
  start.setUTCDate(start.getUTCDate() - 29);
  const from = start.toISOString().slice(0, 10);
  const money = await fetchShop(shopId, "/money", { from, to: today });
  const problem = apiProblem(money, { what: "your product profit", back: `/shops/${shopId}/today` });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["MoneyView"]} */
  const m = money.data;
  const missing = m.coverage?.products_missing ?? 0;
  const profit = m.totals?.gross_profit_after_returns ?? null;
  const soFar = m.totals?.gross_profit_so_far ?? null;
  const base = `/shops/${shopId}`;

  return (
    <section data-testid="profit-reveal">
      <header className="page-head">
        <h1>Your product profit is now clearer.</h1>
        <p>{formatDate(from)} to {formatDate(today)}.</p>
      </header>
      <div className="card" data-testid="profit-reveal-card">
        <ul className="rows">
          <li className="rows__total">
            <span>{profit || !soFar ? "Gross profit after returns" : "Gross profit so far"}</span>
            <Figure amount={profit ?? soFar} reason="No product sold in this period has a cost yet." />
          </li>
          {profit && formatMargin(m.totals.gross_margin_after_returns) && (
            <li><span>Gross margin after returns</span><strong className="money">{formatMargin(m.totals.gross_margin_after_returns)}</strong></li>
          )}
        </ul>
        {missing > 0 ? (
          <p className="card__why" data-testid="profit-reveal-missing">{coverageSentence(m.coverage)}</p>
        ) : (
          <p className="card__why">{BEFORE_OVERHEADS}</p>
        )}
      </div>
      <div className="stack">
        {missing > 0 && <Link className="btn btn--primary btn--block" href={`${base}/setup/costs/manual`}>Review missing costs</Link>}
        <Link className={`btn ${missing > 0 ? "btn--quiet" : "btn--primary"} btn--block`} href={`${base}/products`}>View product performance</Link>
        <Link className="btn btn--quiet btn--block" href={`${base}/returns`}>Review returns</Link>
        <Link className="btn btn--quiet btn--block" href={`${base}/today`}>Go to Overview</Link>
      </div>
    </section>
  );
}
