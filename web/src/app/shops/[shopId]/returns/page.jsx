/**
 * S8 Return check, drawn to wireframe sheet 05. Built 28 September 2026 on checkReturnItem.
 *
 * It lists the returns with an item still to check, from listReturns with
 * `awaiting_check=true`, and gives each waiting item the check form. The sheet shows one
 * return; a seller with several sees each in turn on one page, so none is hidden behind
 * another.
 *
 * Since 10 October 2026 this is the brief's Returns (A36 step 6, section 14): the title and
 * subtitle, the three states (Awaiting inspection, Resellable, Unsellable and written off),
 * and the returns already checked, read only, with what each did to stock and figures. A
 * check stays one way. The brief's optional note is not offered, because the service has
 * nowhere to keep one.
 */

import { fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";
import { ReturnCheckForm } from "@/components/ReturnCheckForm";
import { chipClass } from "@/lib/terms";

export const metadata = { title: "Returns" };

/** The brief's states for a checked item, with the chip tone. @type {Record<string, [string, string, string]>} */
const STATE = {
  resellable: ["Resellable", "good", "Back in stock."],
  unsellable: ["Unsellable, written off", "bad", "Included in your figures."],
  not_applicable: ["Nothing came back", "quiet", "No stock change."],
};

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
  const [result, done] = await Promise.all([
    fetchShop(shopId, "/returns", { awaiting_check: "true" }),
    fetchShop(shopId, "/returns", { awaiting_check: "false", limit: "20" }),
  ]);
  const problem = apiProblem(result, { what: "your returns" });
  if (problem) return problem;
  /** @type {import("@/lib/api-types").components["schemas"]["ReturnSummary"][]} */
  const checkedReturns = done.ok ? (done.data?.returns ?? []) : [];

  /** @type {import("@/lib/api-types").components["schemas"]["ReturnSummary"][]} */
  const returns = result.data.returns ?? [];

  return (
    <section data-testid="returns-screen">
      <header className="page-head">
        <h1>Returns</h1>
        <p>Check each return once.</p>
      </header>

      {checked && RECORDED[checked] && (
        <div className="note note--info" role="status" data-testid="return-recorded"><p>{RECORDED[checked]}</p></div>
      )}

      <h2>Awaiting inspection</h2>
      <p className="muted">Can it be sold again? Each check is final.</p>
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

      {checkedReturns.length > 0 && (
        <>
          <h2>Checked</h2>
          <div className="stack">
            {checkedReturns.flatMap((r) => (r.items ?? []).map((item) => {
              const [word, tone, effect] = STATE[item.seller_check_status] ?? ["Checked", "quiet", ""];
              return (
                <div className="card" key={item.id} data-testid="return-checked">
                  <ul className="rows">
                    <li>
                      <span>
                        {[item.product_title, item.variant_label].filter(Boolean).join(", ") || "A product TikTok did not name"}
                        {`, ${item.quantity} ${item.quantity === 1 ? "unit" : "units"}`}
                      </span>
                      <span className={chipClass(tone)}>{word}</span>
                    </li>
                    <li><span>Order</span><strong>{r.tiktok_order_id}</strong></li>
                    <li><span>Refund to the customer</span><Figure amount={r.refund} reason="Not refunded yet" /></li>
                    {item.checked_at && <li><span>Checked</span><strong>{formatDate(item.checked_at)}</strong></li>}
                    {r.return_cost && r.return_cost.amount_minor !== 0 && (
                      <li><span>Return cost in your figures</span><Figure amount={r.return_cost} /></li>
                    )}
                  </ul>
                  {effect && <p className="card__why">{effect}</p>}
                  {item.seller_note && (
                    <p className="card__why" data-testid="return-note"><strong>Your note:</strong> {item.seller_note}</p>
                  )}
                </div>
              );
            }))}
          </div>
        </>
      )}
    </section>
  );
}
