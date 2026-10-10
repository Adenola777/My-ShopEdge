/**
 * S8 Return check, drawn to wireframe sheet 05. Built 28 September 2026 on checkReturnItem.
 *
 * It lists the returns with an item still to check, from listReturns with
 * `awaiting_check=true`, and gives each waiting item the check form. The sheet shows one
 * return; a seller with several sees each in turn on one page, so none is hidden behind
 * another. Checked items are not listed, because a check is one way.
 */

import { fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";
import { ReturnCheckForm } from "@/components/ReturnCheckForm";

export const metadata = { title: "Check returns" };

/**
 * What a check just recorded, by the status the form put in the address. Each sentence is
 * what checkReturnItem writes for that status (returns.py, A30.2).
 *
 * @type {Record<string, string>}
 */
const RECORDED = {
  resellable: "The check is recorded, and the returned units are back in your stock in MyShopEdge.",
  unsellable: "The check is recorded, and the returned units are written off at the cost in force when they sold.",
  not_applicable: "The check is recorded. Nothing came back, so your stock did not change.",
};

/** @param {{ params: Promise<{ shopId: string }>, searchParams: Promise<Record<string, string>> }} props */
export default async function ReturnsPage({ params, searchParams }) {
  const { shopId } = await params;
  const { checked } = await searchParams;
  const result = await fetchShop(shopId, "/returns", { awaiting_check: "true" });
  const problem = apiProblem(result, { what: "your returns" });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["ReturnSummary"][]} */
  const returns = result.data.returns ?? [];

  return (
    <section data-testid="returns-screen">
      <header className="page-head">
        <h1>Check returns</h1>
        <p>Say whether each returned item can be sold again. Each item can be checked only once, and the check cannot be changed.</p>
      </header>

      {checked && RECORDED[checked] && (
        <div className="note note--info" role="status" data-testid="return-recorded"><p>{RECORDED[checked]}</p></div>
      )}

      {returns.length === 0 ? (
        <div className="card">
          <p className="muted">There are no returns waiting for a check.</p>
        </div>
      ) : (
        <div className="stack">
          {returns.map((r) => {
            const waiting = (r.items ?? []).filter((i) => i.seller_check_status === "pending");
            return waiting.map((item) => (
              <div className="card stack" key={item.id} data-testid="return-to-check">
                <div>
                  <h2>Order {r.tiktok_order_id}</h2>
                  <ul className="rows">
                    <li>
                      <span>Product</span>
                      <strong>
                        {[item.product_title, item.variant_label].filter(Boolean).join(", ") || "A product TikTok did not name"}
                        {`, ${item.quantity} ${item.quantity === 1 ? "unit" : "units"}`}
                      </strong>
                    </li>
                    <li>
                      <span>Refund to the customer</span>
                      <Figure amount={r.refund} reason="Not refunded yet" />
                    </li>
                    {r.requested_at && <li><span>Requested</span><strong>{formatDate(r.requested_at)}</strong></li>}
                  </ul>
                </div>
                <ReturnCheckForm shopId={shopId} itemId={item.id} quantity={item.quantity}
                                 currency={r.refund?.currency ?? "GBP"} />
              </div>
            ));
          })}
        </div>
      )}
    </section>
  );
}
