/**
 * The gross profit reveal, the brief's section 9, approved by the owner under A36 (step 2, 10
 * October 2026). A seller reaches it after saving product costs. It covers the last 30 London
 * days, like the first reconciliation.
 *
 * Every figure is the service's (`getMoney` and `listProducts`). Until A36 step 3, gross
 * profit is served only when every product sold has a cost, so with some costs missing this
 * page shows the cost coverage and the products still missing a cost, and no profit figure.
 * The brief's "share of sales value" wording waits for step 3, which serves that share.
 */

import Link from "next/link";
import { fetchProducts, fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";
import { BEFORE_OVERHEADS, formatMargin } from "@/lib/terms";

export const metadata = { title: "Your product profit" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function ProfitRevealPage({ params }) {
  const { shopId } = await params;
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/London" }).format(new Date());
  const start = new Date(`${today}T12:00:00Z`);
  start.setUTCDate(start.getUTCDate() - 29);
  const from = start.toISOString().slice(0, 10);
  const [money, products] = await Promise.all([
    fetchShop(shopId, "/money", { from, to: today }),
    fetchProducts(shopId, { from, to: today }),
  ]);
  const problem = apiProblem(money, { what: "your product profit", back: `/shops/${shopId}/today` });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["MoneyView"]} */
  const m = money.data;
  /** @type {{ cost_known?: boolean }[]} */
  const rows = products.ok ? products.data?.products ?? [] : [];
  const missing = rows.filter((p) => !p.cost_known).length;
  const profit = m.totals?.gross_profit_after_returns ?? null;
  const coverage = Math.round((m.cost_coverage ?? 0) * 100);
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
            <span>Gross profit after returns</span>
            <Figure amount={profit} reason="Not every product sold has a cost yet, so gross profit cannot be worked out." />
          </li>
          {profit && formatMargin(m.totals.gross_margin_after_returns) && (
            <li><span>Gross margin after returns</span><strong className="money">{formatMargin(m.totals.gross_margin_after_returns)}</strong></li>
          )}
          <li><span>Cost coverage</span><strong>{coverage}% of products sold</strong></li>
        </ul>
        {missing > 0 ? (
          <p className="card__why" data-testid="profit-reveal-missing">
            Costs are still missing for {missing} {missing === 1 ? "product" : "products"}.
          </p>
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
