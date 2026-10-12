/**
 * S22 Records behind a figure.
 *
 * A18.5: every figure a seller sees can be opened, and what opens is the ledger rows that
 * produced it, not a recalculation. `getRecords` serves the rows, the total across every
 * page and the sum of this page, and both totals are shown so that a seller on page one of
 * four does not read the page sum as the figure being wrong.
 *
 * Every category carries the label the service gives it, the same words the Money screen
 * uses. Where TikTok named a fee in a way MyShopEdge does not recognise, TikTok's own name
 * is shown beside it.
 *
 * Not yet here: the discrepancy marker A3 asks for on affected rows, because a ledger entry
 * does not say which discrepancy touches it.
 */

import { Pager } from "@/components/Pager";
import Link from "next/link";
import { fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";

export const metadata = { title: "Transactions" };

const PASSED = [
  "basis", "from", "to", "category", "entry_type", "sku_id", "product_id", "order_id",
  "return_id", "settlement_id",
];

/**
 * @param {{
 *   params: Promise<{ shopId: string }>,
 *   searchParams: Promise<Record<string, string>>,
 * }} props
 */
export default async function RecordsPage({ params, searchParams }) {
  const { shopId } = await params;
  const query = await searchParams;
  /** @type {Record<string, string>} */
  const filters = Object.fromEntries(
    PASSED.filter((k) => query[k]).map((k) => [k, String(query[k])]),
  );

  const result = await fetchShop(shopId, "/records", { ...filters, cursor: query.cursor });
  const problem = apiProblem(result, { what: "these records" });
  if (problem) return problem;

  /** @type {{ entries: import("@/lib/api-types").components["schemas"]["LedgerEntry"][], total: any, shown_total: any, next_cursor: string | null }} */
  const page = result.data;
  const first = page.entries[0];
  const heading = filters.category && first?.label ? first.label : "Transactions";
  const base = `/shops/${shopId}/records`;
  /** True when the page was opened from a figure rather than from the menu. */
  const forFigure = Object.keys(filters).some((k) => k !== "basis" && k !== "from" && k !== "to");

  return (
    <section className="overview">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/money`}>Where the money went</Link></p>
        <h1>{heading}</h1>
        <p>
          {filters.from && filters.to
            ? `${formatDate(filters.from)} to ${formatDate(filters.to)} \u00b7 `
            : ""}
          {filters.basis === "cash" ? "Cash basis" : "Sales basis"}
          {forFigure ? " \u00b7 Records behind this figure" : ""}
        </p>
      </header>

      {page.entries.length === 0 ? (
        <div className="card">
          <p className="muted">{forFigure ? "Nothing recorded against this figure in this period." : "No records match these filters."}</p>
        </div>
      ) : (
        // A37 phase 3: each record is its name and amount, with its date and references on one
        // quiet line under it, joined by a middle dot. TikTok's own field name stays, because an
        // accountant matches it to the statement.
        <div className="card">
          <ul className="rows">
            {page.entries.map((e) => (
              <li key={e.id}>
                <span>
                  {e.label ?? "Record"}
                  <span className="rows__sub" style={{ display: "block" }}>
                    {[
                      formatDate(e.basis_day),
                      e.tiktok_order_id ? `Order ${e.tiktok_order_id}` : e.tiktok_invoice_number ? `Invoice ${e.tiktok_invoice_number}` : null,
                      e.tiktok_fee_type,
                      e.reason,
                    ].filter(Boolean).join(" \u00b7 ")}
                  </span>
                </span>
                <Figure amount={e.amount} />
              </li>
            ))}
            {page.next_cursor && (
              <li className="rows__total"><span>This page</span><Figure amount={page.shown_total} /></li>
            )}
            <li className="rows__total"><span>Total, every page</span><Figure amount={page.total} /></li>
          </ul>
        </div>
      )}

      <Pager
        next={page.next_cursor ? `${base}?${new URLSearchParams({ ...filters, cursor: page.next_cursor })}` : null}
        first={query.cursor ? `${base}?${new URLSearchParams(filters)}` : null}
        label="Transaction pages"
      />
    </section>
  );
}
