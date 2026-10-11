/**
 * S11 Money. Where every pound went, as a running calculation (A8.5).
 *
 * `getMoney` serves the sections, their lines and the running subtotal each section
 * reaches. This screen lays them out in order and does no arithmetic. Every line opens the
 * records behind it on S22, which is the rule A18.5 exists for.
 *
 * Drawn to wireframe sheet 07 (redrawn 24 September after the design audit): the period
 * switch, the basis switch, then the calculation.
 *
 * The period switch. "This month" is the service's default period. "Today" is that
 * period's last day, `period.to`, which is the service's own London date (A29.9), so the
 * browser never decides what day it is. "Tax year" needs the UK tax year's start, which is
 * a rule the contract does not state, so it is not offered until it does.
 *
 * Held and paid out is shown as A18.3 orders it, net proceeds, then the reserve held, then
 * the payout, with no subtotal: adding a payout to a reserve gives a figure with no meaning
 * a seller can use, and the screen showed one until 24 September. The ledger stores the
 * payout and the reserve withheld as negatives, so since 8 October 2026 both are shown
 * without that sign: "-£453.88" beside "Payout" read as money taken from the seller.
 *
 * A fee TikTok names in a way MyShopEdge does not recognise is shown under that heading
 * with TikTok's own name beneath it (A18.4), never as a bare code.
 *
 * Expected payouts by week were read here from `getExpectedPayouts` from 7 October 2026.
 * Since A37 phase 3 (11 October 2026) they are shown on Payouts alone, which already showed
 * the same weeks as Awaiting settlement, so this page is the calculation and nothing else.
 * The switches are the Overview's compact row, and Export sits beside the title.
 */

import Link from "next/link";
import { fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { MoneySections, recordsHref as linesHref } from "@/components/MoneySections";
import { Figure } from "@/components/Figure";
import { BEFORE_OVERHEADS, CONFIDENCE, CONFIDENCE_MEANING, chipClass, coverageSentence, keptReason } from "@/lib/terms";

export const metadata = { title: "Where the money went" };

/**
 * @param {{
 *   params: Promise<{ shopId: string }>,
 *   searchParams: Promise<Record<string, string>>,
 * }} props
 */
export default async function MoneyPage({ params, searchParams }) {
  const { shopId } = await params;
  const query = await searchParams;
  const basis = query.basis === "cash" ? "cash" : "sales";
  const day = query.day;

  const result = await fetchShop(shopId, "/money", { basis, from: day, to: day });
  const problem = apiProblem(result, { what: "your money figures" });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["MoneyView"]} */
  const m = result.data;
  const period = /** @type {{ from: string, to: string }} */ (m.period);
  const [confidence, tone] = CONFIDENCE[m.confidence] ?? [m.confidence, "quiet"];
  const base = `/shops/${shopId}/money`;

  /** @param {{ category?: string | null }} line */
  const recordsHref = (line) => linesHref(shopId, basis, period, line);

  /** The heading and TikTok's name for a line that carries one verbatim. */
  /** @param {any} l */
  /** @param {Record<string, string>} q */
  const href = (q) => `${base}${Object.keys(q).length ? `?${new URLSearchParams(q)}` : ""}`;
  /** @type {Record<string, string>} */
  const withBasis = basis === "cash" ? { basis } : {};

  return (
    <section className="overview">
      <header className="page-head page-head--row">
        <div>
          <h1>Where the money went</h1>
          <p>
            {day ? formatDate(day) : `${formatDate(period.from)} to ${formatDate(period.to)}`}{" "}
            <span className={chipClass(tone)} title={CONFIDENCE_MEANING[m.confidence]}>{confidence}</span>
          </p>
        </div>
        <div className="page-head__actions">
          <Link className="btn btn--quiet btn--small" href={`/shops/${shopId}/money/export`} data-testid="money-export">Export</Link>
        </div>
      </header>

      <div className="toolbar">
        <nav className="switch switch--compact" aria-label="Period">
          <Link href={href({ ...withBasis, day: period.to })} aria-current={day ? "true" : undefined}>Today</Link>
          <Link href={href(withBasis)} aria-current={!day ? "true" : undefined}>This month</Link>
        </nav>
        <nav className="switch switch--compact" aria-label="Basis">
          <Link href={href(day ? { day } : {})} aria-current={basis === "sales" ? "true" : undefined}
                title="Counts money on the day of the sale">Sales basis</Link>
          <Link href={href({ basis: "cash", ...(day ? { day } : {}) })} aria-current={basis === "cash" ? "true" : undefined}
                title="Counts money in the month TikTok settled it">Cash basis</Link>
        </nav>
      </div>

      {(m.unmapped_fee_count ?? 0) > 0 && (
        <div className="note note--warn" role="status">
          <p>
            {m.unmapped_fee_count === 1 ? "One fee has a name MyShopEdge does not recognise." : `${m.unmapped_fee_count} fees have names MyShopEdge does not recognise.`}{" "}
            Counted in full under TikTok&apos;s name.{" "}
            <Link href={recordsHref({ category: "unmapped_fee" })}>
              {m.unmapped_fee_count === 1 ? "See the fee" : "See the fees"}
            </Link>
          </p>
        </div>
      )}

      {m.sections.length === 0 ? (
        <div className="card" data-testid="money-empty">
          <p className="muted">Nothing recorded in this period.</p>
        </div>
      ) : (
        <>
          {/* The sections are third-level headings, as on Overview, so the page names the
              calculation at the second level for a screen reader (A37 phase 6, axe-core). */}
          <h2 className="visually-hidden">The calculation, line by line</h2>
          <MoneySections m={m} shopId={shopId} basis={basis} />
        </>
      )}

      {m.totals?.gross_profit_so_far && (
        <div className="card overview__more" data-testid="money-so-far">
          <ul className="rows">
            <li className="rows__total"><span>Gross profit so far</span><Figure amount={m.totals.gross_profit_so_far} /></li>
          </ul>
          {coverageSentence(m.coverage) && <p className="card__why">{coverageSentence(m.coverage)}</p>}
          <p className="hero__action"><Link href={`/shops/${shopId}/setup/costs/manual`}>Review missing costs</Link></p>
        </div>
      )}

      <p className="footnote overview__note">
        {m.kept || m.totals?.gross_profit_so_far ? BEFORE_OVERHEADS : keptReason(m.kept_reason)}
      </p>
    </section>
  );
}
