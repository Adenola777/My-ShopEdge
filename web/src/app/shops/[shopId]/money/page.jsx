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
 * Expected payouts by week are read from `getExpectedPayouts`, which asks TikTok for the
 * shop's unsettled transactions when the page opens (7 October 2026). Every figure there is
 * TikTok's estimate and is labelled as one. If TikTok does not answer, that card says so and
 * the rest of the page is unaffected.
 */

import Link from "next/link";
import { fetchShop, formatDate, formatMoney } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { LineLabel } from "@/components/LineLabel";
import { Figure } from "@/components/Figure";
import { BEFORE_OVERHEADS, CONFIDENCE, CONFIDENCE_MEANING, chipClass, keptReason } from "@/lib/terms";

/** Lines whose label states their direction, shown without the ledger's sign. */
const UNSIGNED = new Set(["settlement", "reserve_withheld"]);

export const metadata = { title: "Money" };

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

  const [result, expected] = await Promise.all([
    fetchShop(shopId, "/money", { basis, from: day, to: day }),
    fetchShop(shopId, "/payouts/expected"),
  ]);
  const problem = apiProblem(result, { what: "your money figures" });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["MoneyView"]} */
  const m = result.data;
  const period = /** @type {{ from: string, to: string }} */ (m.period);
  const [confidence, tone] = CONFIDENCE[m.confidence] ?? [m.confidence, "quiet"];
  const base = `/shops/${shopId}/money`;

  /** @param {{ category?: string | null }} line */
  const recordsHref = (line) =>
    `/shops/${shopId}/records?${new URLSearchParams({
      basis,
      from: period.from,
      to: period.to,
      ...(line.category ? { category: line.category } : {}),
    })}`;

  /** The heading and TikTok's name for a line that carries one verbatim. */
  /** @param {any} l */
  /** @param {Record<string, string>} q */
  const href = (q) => `${base}${Object.keys(q).length ? `?${new URLSearchParams(q)}` : ""}`;
  /** @type {Record<string, string>} */
  const withBasis = basis === "cash" ? { basis } : {};

  return (
    <section>
      <header className="page-head">
        <h1>Money</h1>
        <p>
          This shows where every pound went{" "}
          {day ? `on ${formatDate(day)}` : `from ${formatDate(period.from)} to ${formatDate(period.to)}`}.{" "}
          <span className={chipClass(tone)} title={CONFIDENCE_MEANING[m.confidence]}>{confidence}</span>
        </p>
      </header>

      <nav className="switch" aria-label="Period">
        <Link href={href({ ...withBasis, day: period.to })} aria-current={day ? "true" : undefined}>Today</Link>
        <Link href={href(withBasis)} aria-current={!day ? "true" : undefined}>This month</Link>
      </nav>
      <nav className="switch" aria-label="Basis">
        <Link href={href(day ? { day } : {})} aria-current={basis === "sales" ? "true" : undefined}>Sales basis</Link>
        <Link href={href({ basis: "cash", ...(day ? { day } : {}) })} aria-current={basis === "cash" ? "true" : undefined}>Cash basis</Link>
      </nav>
      <p className="rows__sub">
        {basis === "sales" ? "Sales basis counts money on the day of the sale." : "Cash basis counts money in the month TikTok settled it."}
      </p>
      <p><Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/payouts`} data-testid="money-payouts">
        Payouts and fee invoices
      </Link></p>

      {(m.unmapped_fee_count ?? 0) > 0 && (
        <div className="note note--warn" role="status">
          <p>
            {m.unmapped_fee_count === 1
              ? "One fee in this period has a name MyShopEdge does not recognise."
              : `${m.unmapped_fee_count} fees in this period have names MyShopEdge does not recognise.`}{" "}
            The money is counted in full, under the name TikTok gave it.{" "}
            <Link href={recordsHref({ category: "unmapped_fee" })}>
              {m.unmapped_fee_count === 1 ? "See the fee" : "See the fees"}
            </Link>
          </p>
        </div>
      )}

      <div className="stack">
        {m.sections.map((s) => (
          <div className="card" key={s.key}>
            <h2>{s.label}</h2>
            <ul className="rows">
              {s.lines.map((l, i) => (
                <li key={`${l.category}-${l.tiktok_fee_type ?? i}`}>
                  <Link className="rowlink rowlink--quiet" href={recordsHref(l)}><LineLabel line={l} /></Link>
                  <Figure amount={l.amount} unsigned={UNSIGNED.has(l.category ?? "")} />
                </li>
              ))}
              {s.key !== "payout" && (
                <li className="rows__total">
                  <span>{s.subtotal_label ?? "Subtotal"}</span>
                  <Figure amount={s.subtotal} reason={s.key === "return_costs" ? keptReason(m.kept_reason) : null} />
                </li>
              )}
            </ul>
          </div>
        ))}
      </div>

      <ExpectedPayouts result={expected} shopId={shopId} />

      <p className="footnote">
        {m.kept ? BEFORE_OVERHEADS : keptReason(m.kept_reason)}
      </p>
      <p><Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/money/export`} data-testid="money-export">Export this for your accountant</Link></p>
    </section>
  );
}

/**
 * TikTok's unsettled transactions grouped by the week TikTok expects to pay them. The
 * service does the grouping and the sums; this only lays them out.
 *
 * @param {{ result: import("@/lib/api").ApiResult, shopId: string }} props
 */
function ExpectedPayouts({ result, shopId }) {
  if (!result.ok || !result.data) {
    return (
      <div className="card" data-testid="expected-payouts">
        <h2>Expected payouts</h2>
        <p className="card__why">
          {result.status === 409 ? (
            <>
              This shop is not connected to TikTok, so MyShopEdge cannot ask TikTok what it
              expects to pay.{" "}
              <Link href={`/shops/${shopId}/connection-problem`}>Reconnect your shop</Link>
            </>
          ) : "TikTok did not answer just now, so expected payouts are not shown. The figures above are unaffected."}
        </p>
      </div>
    );
  }
  /** @type {import("@/lib/api-types").components["schemas"]["ExpectedPayouts"]} */
  const p = result.data;
  const [estLabel, estTone] = CONFIDENCE.estimated ?? ["Estimated", "strong"];
  return (
    <div className="card" data-testid="expected-payouts">
      <h2>Expected payouts <span className={chipClass(estTone)}>{estLabel}</span></h2>
      {p.weeks.length === 0 ? (
        <p className="card__why">TikTok holds no unsettled orders for this shop.</p>
      ) : (
        <ul className="rows">
          {p.weeks.map((w) => (
            <li key={w.week_starting}>
              <span>
                Week of {formatDate(w.week_starting)}
                {w.orders > 0 ? `, ${w.orders} ${w.orders === 1 ? "order" : "orders"}` : ""}
              </span>
              <Figure amount={w.amount} />
            </li>
          ))}
          <li className="rows__total">
            <span>Total expected</span>
            <Figure amount={p.total} />
          </li>
        </ul>
      )}
      {p.weeks.length > 0 && (
        <p className="card__why">
          These are TikTok&apos;s own estimates of {formatMoney(p.total)} still to come, and they can
          change before TikTok settles. An order leaves this list once it is settled and appears in
          the figures above.
        </p>
      )}
      <p className="card__why">
        TikTok works these figures out itself, so they can differ from Awaiting settlement on
        Today, which MyShopEdge counts from its own records.
      </p>
    </div>
  );
}
