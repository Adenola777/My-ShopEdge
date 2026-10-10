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
 *
 * Since 10 October 2026 this is the brief's Explain this payout (A36 step 5): the payout
 * received, its status, the linked statement, the difference and a plain sentence on what the
 * status means, then the statement's parts, the orders it includes and when each figure was
 * read. The status is the service's (`reconcile_status`); this page only words it. TikTok's
 * statement does not state refunds on their own, so they sit inside net sales here, as
 * TikTok counts them, and are not shown as a separate line.
 */

import Link from "next/link";
import { api, fetchShop, formatDate, formatMoney } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";
import { InvoiceForm } from "@/components/InvoiceForm";
import { LineLabel } from "@/components/LineLabel";
import { UpgradePrompt } from "@/components/UpgradePrompt";
import { PAYOUT_STATUS, chipClass } from "@/lib/terms";

export const metadata = { title: "Explain this payout" };

/**
 * What the payout's status means, in a sentence. Normal timing is never described as a fault.
 *
 * @param {import("@/lib/api-types").components["schemas"]["Settlement"]} s
 * @param {import("@/lib/api-types").components["schemas"]["SettlementReconciliation"]} r
 */
function explanation(s, r) {
  const diff = formatMoney({ ...r.unexplained, amount_minor: Math.abs(r.unexplained.amount_minor) });
  const orders = `${r.orders_settled} ${r.orders_settled === 1 ? "order" : "orders"}`;
  switch (s.reconcile_status) {
    case "reconciled":
      return `TikTok paid this statement${s.paid_at ? ` on ${formatDate(s.paid_at)}` : ""}. The ${orders} behind it add up to it exactly, after TikTok's fees and any reserve it held back.`;
    case "pending_payment":
      return "TikTok has issued this statement and has not paid it yet. This is normal timing, and MyShopEdge will show the payment once TikTok reports it.";
    case "sync_delayed":
      return "TikTok had not paid this statement when MyShopEdge last read it, and that read failed or is more than a day old, so the payment may have moved on since. The status updates after the next successful read.";
    case "needs_review":
      return s.payment_status === "FAILED"
        ? "TikTok reports that this payment failed. Check the bank account TikTok pays into in your TikTok Seller Center."
        : `The ${orders} behind this statement differ from it by ${diff}. MyShopEdge shows the difference rather than hiding it, so you can check the statement in your TikTok Seller Center.`;
    default:
      return "MyShopEdge could not work out a status for this payout.";
  }
}

/** @param {{ params: Promise<{ shopId: string, settlementId: string }> }} props */
export default async function PayoutPage({ params }) {
  const { shopId, settlementId } = await params;
  const [result, subRes] = await Promise.all([
    fetchShop(shopId, `/settlements/${encodeURIComponent(settlementId)}`),
    api("/billing/subscription", { cache: "no-store" }),
  ]);
  const problem = apiProblem(result, { what: "this payout", notFound: "That payout is not on your account." });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["SettlementDetail"]} */
  const d = result.data;
  const s = d.settlement;
  const c = d.components;
  const r = d.reconciliation;
  const inv = d.invoice;
  const orderList = d.orders ?? [];
  const unexplained = r.unexplained.amount_minor !== 0;
  // The pricing ruling of 10 October 2026 offers Pro's review list to a Growth seller who opens
  // statements that need review. Starter is offered Growth first, so it sees no prompt here.
  const features = subRes.ok ? (subRes.data?.features ?? []) : [];
  const offerReview = unexplained && features.includes("exports") && !features.includes("priority_review");
  const feeLines = c.fee_lines ?? [];
  const feeLinesTotal = feeLines.reduce((sum, l) => sum + l.amount.amount_minor, 0);
  const feeLinesShort = feeLines.length > 0 && feeLinesTotal !== c.fees.amount_minor;

  return (
    <section data-testid="payout-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/payouts`}>Payouts</Link></p>
        <h1>Explain this payout</h1>
        <p>Statement of {formatDate(s.statement_time)}, TikTok statement {s.tiktok_statement_id}</p>
      </header>

      <div className="stack">
        <div className="card" data-testid="payout-explained">
          <ul className="rows">
            <li className="rows__total">
              <span>Payout received</span>
              {s.payment_status === "PAID" ? <Figure amount={s.payable_amount} /> : <span className="muted">Not paid yet</span>}
            </li>
            <li>
              <span>Status</span>
              {(() => {
                const [word, tone] = PAYOUT_STATUS[s.reconcile_status ?? ""] ?? ["Status not known", "quiet"];
                return <span className={chipClass(tone)} data-testid="payout-status">{word}</span>;
              })()}
            </li>
            <li><span>Linked statement</span><span>{formatDate(s.statement_time)}, <Figure amount={s.statement_amount} /></span></li>
            <li><span>Difference</span><Figure amount={r.unexplained} /></li>
          </ul>
          <p className="card__why" data-testid="payout-explanation">{explanation(s, r)}</p>
        </div>

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

        <div className="card" data-testid="payout-orders">
          <h2>Included orders</h2>
          {orderList.length === 0 ? (
            <p className="card__why">MyShopEdge holds no order lines for this statement.</p>
          ) : (
            <details className="disclose">
              <summary>{orderList.length} {orderList.length === 1 ? "order" : "orders"} on this statement</summary>
              <ul className="rows">
                {orderList.map((o) => (
                  <li key={o.order_id}>
                    <span>Order {o.tiktok_order_id}</span>
                    <Figure amount={o.settled} reason="No sale is recorded for this order on this statement." />
                  </li>
                ))}
              </ul>
            </details>
          )}
          <p className="card__why">
            Orders TikTok has not yet put on a statement are shown under Awaiting settlement on{" "}
            <Link href={`/shops/${shopId}/payouts`}>Reconcile</Link>.
          </p>
        </div>

        <div className="card" data-testid="payout-sources">
          <h2>When these figures were read</h2>
          <ul className="rows">
            <li><span>TikTok issued the statement</span><strong>{formatDate(s.statement_time, { time: true })}</strong></li>
            <li><span>TikTok paid it</span><strong>{s.paid_at ? formatDate(s.paid_at, { time: true }) : "Not yet"}</strong></li>
            <li>
              <span>MyShopEdge last read TikTok&apos;s statements</span>
              <strong>{d.finance_read_at ? formatDate(d.finance_read_at, { time: true }) : "Not yet"}</strong>
            </li>
          </ul>
        </div>

        {offerReview ? (
          <UpgradePrompt feature="priority_review" plan="pro" back={`/shops/${shopId}/payouts`} compact />
        ) : null}

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
