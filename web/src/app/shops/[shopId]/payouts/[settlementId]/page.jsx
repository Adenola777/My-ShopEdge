/**
 * One payout, from `getSettlement`: what TikTok's statement says, how its parts add up,
 * whether the orders behind it explain it, and the TikTok fee invoice billed against it.
 *
 * Built 7 October 2026. TikTok offers no API for a seller's fee invoices (A9.8), so the
 * seller copies the invoice from Seller Center into the form at the foot of the page. The
 * service checks that gross equals net plus VAT and holds the invoice for six years. The
 * PDF itself is not stored yet, for the reason A10 gives.
 *
 * Since 9 October 2026 each fee is on its own line, named as Money names it (A8.3), with
 * Total TikTok fees directly under the lines. A statement whose ledger holds no fee lines
 * keeps the single Fees line, so no amount drops off the page.
 */

import Link from "next/link";
import { fetchShop, formatDate, formatMoney } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";
import { InvoiceForm } from "@/components/InvoiceForm";
import { LineLabel } from "@/components/LineLabel";

export const metadata = { title: "Payout" };

/** @param {{ params: Promise<{ shopId: string, settlementId: string }> }} props */
export default async function PayoutPage({ params }) {
  const { shopId, settlementId } = await params;
  const result = await fetchShop(shopId, `/settlements/${encodeURIComponent(settlementId)}`);
  const problem = apiProblem(result, { what: "this payout", notFound: "That payout is not on your account." });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["SettlementDetail"]} */
  const d = result.data;
  const s = d.settlement;
  const c = d.components;
  const r = d.reconciliation;
  const inv = d.invoice;
  const unexplained = r.unexplained.amount_minor !== 0;
  const feeLines = c.fee_lines ?? [];
  const feeLinesTotal = feeLines.reduce((sum, l) => sum + l.amount.amount_minor, 0);
  const feeLinesShort = feeLines.length > 0 && feeLinesTotal !== c.fees.amount_minor;

  return (
    <section data-testid="payout-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/payouts`}>Payouts</Link></p>
        <h1>Payout of {formatDate(s.statement_time)}</h1>
        <p>TikTok statement {s.tiktok_statement_id}</p>
      </header>

      <div className="stack">
        <div className="card">
          <h2>What TikTok&apos;s statement says</h2>
          <ul className="rows">
            <li><span>Net sales</span><Figure amount={c.net_sales} /></li>
            {feeLines.length > 0 ? (
              <>
                {feeLines.map((l, i) => (
                  <li key={`${l.category}-${l.tiktok_field ?? ""}-${i}`}>
                    <span><LineLabel line={l} /></span><Figure amount={l.amount} />
                  </li>
                ))}
                <li className="rows__total"><span>Total TikTok fees</span><Figure amount={c.fees} /></li>
              </>
            ) : (
              <li><span>Fees</span><Figure amount={c.fees} /></li>
            )}
            <li><span>Shipping cost charged by TikTok</span><Figure amount={c.shipping_cost} /></li>
            <li><span>TikTok adjustments</span><Figure amount={c.adjustments} /></li>
            {c.difference && c.difference.amount_minor !== 0 && (
              <li><span>Not explained by TikTok</span><Figure amount={c.difference} /></li>
            )}
            <li className="rows__total"><span>Statement total</span><Figure amount={s.statement_amount} /></li>
            <li><span>Reserve withheld</span><Figure amount={s.total_reserve} unsigned /></li>
            <li className="rows__total"><span>Paid out</span><Figure amount={s.payable_amount} /></li>
          </ul>
          {feeLinesShort && (
            <p className="card__why">
              The fee lines above do not add up to the fees TikTok&apos;s statement states. Total
              TikTok fees shows TikTok&apos;s own figure.
            </p>
          )}
        </div>

        <div className="card">
          <h2>Do the orders add up to this statement?</h2>
          <ul className="rows">
            <li><span>Orders settled</span><strong>{r.orders_settled}</strong></li>
            <li><span>Net proceeds from those orders</span><Figure amount={r.net_proceeds} /></li>
            <li className="rows__total"><span>Unexplained</span><Figure amount={r.unexplained} /></li>
          </ul>
          <p className="card__why">
            {/* A18.3 asks for a route to Discrepancies here, but nothing raises a discrepancy for
                a statement that does not reconcile, so no link is offered (copy audit finding 46). */}
            {unexplained
              ? `The orders behind this statement differ from it by ${formatMoney({ ...r.unexplained, amount_minor: Math.abs(r.unexplained.amount_minor) })}. MyShopEdge shows the difference as Unexplained rather than hiding it.`
              : "The orders behind this statement add up to it exactly."}
          </p>
        </div>

        <div className="card" data-testid="payout-invoice">
          <h2>TikTok fee invoice</h2>
          {inv ? (
            <ul className="rows">
              <li><span>Number</span><strong>{inv.invoice_number}</strong></li>
              <li><span>Type</span><strong>{inv.invoice_type}</strong></li>
              <li><span>Issued</span><strong>{formatDate(inv.issued_on)}</strong></li>
              {inv.period_start && inv.period_end && (
                <li><span>Period</span><strong>{formatDate(inv.period_start)} to {formatDate(inv.period_end)}</strong></li>
              )}
              <li><span>Net</span><Figure amount={inv.net} /></li>
              <li><span>VAT</span><Figure amount={inv.vat} /></li>
              <li className="rows__total"><span>Gross</span><Figure amount={inv.gross} /></li>
            </ul>
          ) : (
            <p className="card__why">
              {s.tiktok_invoice_number
                ? `Invoice ${s.tiktok_invoice_number} is noted, but its amounts are not recorded yet.`
                : "No invoice is recorded for this payout yet."}{" "}
              TikTok does not send invoices to apps, so copy it from your TikTok Seller Center.
            </p>
          )}
          <InvoiceForm shopId={shopId} settlementId={s.id} currency={s.statement_amount.currency}
                       invoice={inv ?? null} />
        </div>
      </div>
    </section>
  );
}
