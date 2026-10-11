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
      return `The ${orders} behind it add up exactly, after fees and any reserve.`;
    case "pending_payment":
      return "Issued, not paid yet. This is normal timing.";
    case "sync_delayed":
      return "Not paid at the last read, which is over a day old. Updates after the next read.";
    case "needs_review":
      return s.payment_status === "FAILED"
        ? "TikTok reports this payment failed. Check your bank details in TikTok Seller Center."
        : `The ${orders} behind it differ by ${diff}. Check the statement in TikTok Seller Center.`;
    default:
      return "No status could be worked out for this payout.";
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

  const [word, tone] = PAYOUT_STATUS[s.reconcile_status ?? ""] ?? ["Status not known", "quiet"];
  const failed = s.payment_status === "FAILED";

  // A37 phase 3, 11 October 2026: the Overview's pattern. The payout and its status as the main
  // figure, the statement as one card of groups each closed by its subtotal, the check against
  // the orders with the orders folded inside it, and the invoice. The times each figure was
  // read moved into the main card's line of facts, and the difference is stated once.
  return (
    <section className="overview" data-testid="payout-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/payouts`}>Payouts</Link></p>
        <h1>Explain this payout</h1>
        <p>TikTok statement {s.tiktok_statement_id}</p>
      </header>

      <div className="card hero" data-testid="payout-explained">
        <p className="hero__label">
          {s.payment_status === "PAID" ? "Payout received" : failed ? "Payout failed" : "Payout due"}{" "}
          <span className={chipClass(tone)} data-testid="payout-status">{word}</span>
        </p>
        <p className="hero__value">
          {failed ? <Figure amount={s.payable_amount} alert /> : <Figure amount={s.payable_amount} />}
        </p>
        <p className="hero__line" data-testid="payout-explanation">{explanation(s, r)}</p>
        <p className="hero__meta" data-testid="payout-sources">
          <span>Issued {formatDate(s.statement_time, { time: true })}</span>
          <span>{s.paid_at ? `Paid ${formatDate(s.paid_at, { time: true })}` : "Not paid yet"}</span>
          <span>{d.finance_read_at ? `Read ${formatDate(d.finance_read_at, { time: true })}` : "Not read yet"}</span>
        </p>
      </div>

      <h2 className="overview__heading">How the statement adds up</h2>
      <div className="card statement" data-testid="payout-statement">
        <div className="statement__group">
          <ul className="rows">
            <li><span>Net sales</span><Figure amount={c.net_sales} /></li>
          </ul>
        </div>
        <div className="statement__group">
          <p className="statement__label">TikTok fees</p>
          <ul className="rows">
            {feeLines.length > 0 ? (
              feeLines.map((l, i) => (
                <li key={`${l.category}-${l.tiktok_field ?? ""}-${i}`}>
                  <span><LineLabel line={l} /></span><Figure amount={l.amount} />
                </li>
              ))
            ) : null}
            <li className={feeLines.length > 0 ? "rows__total" : undefined}><span>{feeLines.length > 0 ? "Total TikTok fees" : "Fees"}</span><Figure amount={c.fees} /></li>
          </ul>
          {feeLinesShort && <p className="rows__sub">The lines do not add up to TikTok&apos;s fee total, which is shown.</p>}
        </div>
        <div className="statement__group">
          <p className="statement__label">Other deductions</p>
          <ul className="rows">
            <li><span>Shipping charged by TikTok</span><Figure amount={c.shipping_cost} /></li>
            <li><span>TikTok adjustments</span><Figure amount={c.adjustments} /></li>
            {c.difference && c.difference.amount_minor !== 0 && (
              <li><span>Not explained by TikTok</span><Figure amount={c.difference} review /></li>
            )}
            <li className="rows__total"><span>Statement total</span><Figure amount={s.statement_amount} /></li>
          </ul>
        </div>
        <div className="statement__group">
          <ul className="rows">
            <li><span>Reserve withheld</span><Figure amount={s.total_reserve} unsigned /></li>
            <li className="rows__total"><span>{s.payment_status === "PAID" ? "Paid out" : "To be paid"}</span><Figure amount={s.payable_amount} /></li>
          </ul>
        </div>
      </div>

      <h2 className="overview__heading">Checked against your orders</h2>
      <div className="card" data-testid="payout-orders">
        {/* A18.3 asks for a route to Discrepancies here, but nothing raises a discrepancy for
            a statement that does not reconcile, so no link is offered (copy audit finding 46). */}
        <ul className="rows">
          <li><span>Orders settled</span><strong>{r.orders_settled}</strong></li>
          <li><span>Their net proceeds</span><Figure amount={r.net_proceeds} /></li>
          <li className="rows__total"><span>Difference</span><Figure amount={r.unexplained} review /></li>
        </ul>
        {orderList.length > 0 ? (
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
        ) : (
          <p className="rows__sub">No order lines held for this statement.</p>
        )}
      </div>

      {offerReview ? (
        <div className="overview__more">
          <UpgradePrompt feature="priority_review" plan="pro" back={`/shops/${shopId}/payouts`} compact />
        </div>
      ) : null}

      <h2 className="overview__heading">TikTok fee invoice</h2>
      <div className="card" data-testid="payout-invoice">
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
            {s.tiktok_invoice_number ? `Invoice ${s.tiktok_invoice_number} noted, amounts not added.` : "No invoice added."}{" "}
            Copy it from TikTok Seller Center.
          </p>
        )}
        {inv ? (
          <InvoiceForm shopId={shopId} settlementId={s.id} currency={s.statement_amount.currency} invoice={inv} />
        ) : (
          <details className="disclose" data-testid="invoice-add">
            <summary>Add the invoice</summary>
            <InvoiceForm shopId={shopId} settlementId={s.id} currency={s.statement_amount.currency} invoice={null} />
          </details>
        )}
      </div>
    </section>
  );
}
