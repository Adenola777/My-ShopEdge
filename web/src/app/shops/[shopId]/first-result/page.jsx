/**
 * The first reconciliation, the brief's section 6 ("First value moment"), approved by the owner
 * under A36 (step 2, 10 October 2026). It is shown once: from the trial active page, or from
 * the import page when the import has finished. After it, Overview is the first screen.
 *
 * Every figure is the service's (`getMoney`, the same calculator Money uses), for the last 30
 * London days. The lines and subtotals are shown as served, in the service's order, so this
 * page changes with the service when A36 step 3 moves refunds above net sales; nothing is
 * added up here. Gross profit appears only when the service has one, which needs product costs.
 */

import Link from "next/link";
import { fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";
import { LineLabel } from "@/components/LineLabel";
import { BEFORE_OVERHEADS, formatMargin } from "@/lib/terms";

export const metadata = { title: "Your first reconciliation" };

/** The chain up to net proceeds. Costs, return costs and the payout are not part of it. */
const FIRST_SECTIONS = new Set(["revenue", "tiktok_fees", "refunds"]);

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function FirstResultPage({ params }) {
  const { shopId } = await params;
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/London" }).format(new Date());
  const start = new Date(`${today}T12:00:00Z`);
  start.setUTCDate(start.getUTCDate() - 29);
  const from = start.toISOString().slice(0, 10);
  const result = await fetchShop(shopId, "/money", { from, to: today });
  const problem = apiProblem(result, { what: "your first reconciliation", back: `/shops/${shopId}/today` });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["MoneyView"]} */
  const m = result.data;
  const sections = m.sections.filter((s) => FIRST_SECTIONS.has(s.key));
  const records = (/** @type {{ category?: string | null }} */ line) =>
    `/shops/${shopId}/records?${new URLSearchParams({
      basis: "sales", from, to: today, ...(line.category ? { category: line.category } : {}),
    })}`;
  const profit = m.totals?.gross_profit_after_returns ?? null;

  return (
    <section data-testid="first-result">
      <header className="page-head">
        <h1>Your first reconciliation is ready.</h1>
        <p>Here is what TikTok Shop has left you for {formatDate(from)} to {formatDate(today)}.</p>
      </header>

      {sections.length === 0 ? (
        <div className="card" data-testid="first-result-empty">
          <p>MyShopEdge holds no sales, fees or refunds for these 30 days yet. Your figures fill in as your shop is read.</p>
        </div>
      ) : (
        <div className="stack">
          {sections.map((s) => (
            <div className="card" key={s.key}>
              <h2>{s.label}</h2>
              <ul className="rows">
                {s.lines.map((l, i) => (
                  <li key={`${l.category}-${l.tiktok_fee_type ?? i}`}>
                    <Link className="rowlink rowlink--quiet" href={records(l)}><LineLabel line={l} /></Link>
                    <Figure amount={l.amount} />
                  </li>
                ))}
                <li className="rows__total">
                  <span>{s.subtotal_label ?? "Subtotal"}</span>
                  <Figure amount={s.subtotal} />
                </li>
              </ul>
            </div>
          ))}
          {profit && (
            <div className="card" data-testid="first-result-profit">
              <ul className="rows">
                <li className="rows__total"><span>Gross profit after returns</span><Figure amount={profit} /></li>
                {formatMargin(m.totals.gross_margin_after_returns) && (
                  <li><span>Gross margin after returns</span><strong className="money">{formatMargin(m.totals.gross_margin_after_returns)}</strong></li>
                )}
              </ul>
              <p className="card__why">{BEFORE_OVERHEADS}</p>
            </div>
          )}
        </div>
      )}

      <p className="card__why">
        Net proceeds are what remain after TikTok Shop deductions, before product costs.
      </p>
      <p className="footnote">
        Your figures are based on the orders, fees, refunds, statements and payouts currently
        available from your shop. Open any line to see the activity behind it.
      </p>
      <p>
        <Link className="btn btn--primary btn--block" href={`/shops/${shopId}/today`} data-testid="first-result-explore">
          Explore my figures
        </Link>
      </p>
      {!profit && (
        <p>
          <Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/setup/costs`} data-testid="first-result-costs">
            Add product costs
          </Link>
        </p>
      )}
    </section>
  );
}
