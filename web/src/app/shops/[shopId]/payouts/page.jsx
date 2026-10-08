/**
 * Payouts: the statements TikTok has issued, newest first, from `listSettlements`.
 *
 * Built 7 October 2026 so a seller can reach each payout and record its TikTok fee invoice.
 * Each row shows what the statement says, what TikTok held back and what reaches the bank,
 * because those three differ whenever TikTok holds a reserve (A18.3), and whether the
 * invoice has been recorded.
 */

import Link from "next/link";
import { fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";

export const metadata = { title: "Payouts" };

/** TikTok's payment status, in words. */
const STATUS = { PAID: "Paid", PROCESSING: "Being paid", FAILED: "Payment failed" };

/** @param {{ params: Promise<{ shopId: string }>, searchParams: Promise<Record<string, string>> }} props */
export default async function PayoutsPage({ params, searchParams }) {
  const { shopId } = await params;
  const { cursor } = await searchParams;
  const result = await fetchShop(shopId, "/settlements", { cursor, limit: "50" });
  const problem = apiProblem(result, { what: "your payouts" });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["Settlement"][]} */
  const rows = result.data.settlements ?? [];
  const next = result.data.next_cursor;

  return (
    <section data-testid="payouts-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/money`}>Money</Link></p>
        <h1>Payouts</h1>
        <p>Every statement TikTok has issued, with what reached your bank and its fee invoice.</p>
      </header>

      {rows.length === 0 ? (
        <div className="card"><p className="muted">TikTok has not issued a statement for this shop yet.</p></div>
      ) : (
        <div className="stack">
          {rows.map((s) => (
            <Link key={s.id} href={`/shops/${shopId}/payouts/${s.id}`} className="card rowlink" data-testid="payout-row">
              <h2>{formatDate(s.statement_time)}</h2>
              <ul className="rows">
                <li><span>Statement total</span><Figure amount={s.statement_amount} /></li>
                <li><span>Reserve withheld</span><Figure amount={s.total_reserve} unsigned /></li>
                <li className="rows__total"><span>Paid out</span><Figure amount={s.payable_amount} /></li>
                <li><span>Status</span><strong>{STATUS[/** @type {keyof typeof STATUS} */ (s.payment_status)] ?? "Status not known"}</strong></li>
                <li>
                  <span>Fee invoice</span>
                  <strong>{s.tiktok_invoice_number ?? "Not recorded"}</strong>
                </li>
              </ul>
            </Link>
          ))}
        </div>
      )}

      {next && (
        <p><Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/payouts?${new URLSearchParams({ cursor: next })}`}>Older payouts</Link></p>
      )}
    </section>
  );
}
