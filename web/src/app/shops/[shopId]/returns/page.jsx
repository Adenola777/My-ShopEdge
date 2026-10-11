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
 *
 * A37 phase 6, 11 October 2026: the checked returns are one list, a row each, where each had
 * been a card of five lines. A row carries the product, its order, the check's date and any
 * note on one quiet line, and the state and refund on the right, with the cost written off
 * under the refund when there is one. Returns waiting for a check keep their cards, because
 * each holds its form.
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

  /** A product and its quantity, in a few words. @param {any} item */
  const what = (item) => `${[item.product_title, item.variant_label].filter(Boolean).join(", ") || "A product TikTok did not name"}${item.quantity === 1 ? "" : `, ${item.quantity} units`}`;

  return (
    <section className="overview" data-testid="returns-screen">
      <header className="page-head">
        <h1>Returns</h1>
        <p>Check each return once. Each check is final.</p>
      </header>

      {checked && RECORDED[checked] && (
        <div className="note note--info" role="status" data-testid="return-recorded"><p>{RECORDED[checked]}</p></div>
      )}

      <h2 className="overview__heading">Awaiting inspection</h2>
      {returns.length === 0 ? (
        <div className="card">
          <p className="overview__clear"><span aria-hidden="true">{"\u2713"}</span> No returns waiting for a check.</p>
        </div>
      ) : (
        <div className="stack">
          {returns.map((r) => {
            const waiting = (r.items ?? []).filter((i) => i.seller_check_status === "pending");
            return waiting.map((item) => (
              <div className="card" key={item.id} data-testid="return-to-check">
                <p className="hero__label">{what(item)}</p>
                <p className="hero__meta">
                  <span>Order {r.tiktok_order_id}</span>
                  {r.requested_at && <span>Requested {formatDate(r.requested_at)}</span>}
                  <span>Refund <Figure amount={r.refund} reason="Not refunded yet" /></span>
                </p>
                <ReturnCheckForm shopId={shopId} itemId={item.id} quantity={item.quantity}
                                 currency={r.refund?.currency ?? "GBP"} />
              </div>
            ));
          })}
        </div>
      )}

      {checkedReturns.length > 0 && (
        <>
          <h2 className="overview__heading">Checked</h2>
          <div className="card">
            <ul className="rows">
              {checkedReturns.flatMap((r) => (r.items ?? []).map((item) => {
                const [word, tone, effect] = STATE[item.seller_check_status] ?? ["Checked", "quiet", ""];
                const cost = r.return_cost && r.return_cost.amount_minor !== 0 ? r.return_cost : null;
                return (
                  <li key={item.id} data-testid="return-checked">
                    <span>
                      <span className="payouts__when">{what(item)}</span>
                      <span className="rows__sub products__sub">
                        {[`Order ${r.tiktok_order_id}`, item.checked_at ? `Checked ${formatDate(item.checked_at)}` : null, effect].filter(Boolean).join(" \u00b7 ")}
                      </span>
                      {item.seller_note && (
                        <span className="rows__sub products__sub" data-testid="return-note">Your note: {item.seller_note}</span>
                      )}
                    </span>
                    <span className="products__figure">
                      <span className={chipClass(tone)}>{word}</span>
                      <span>Refund <Figure amount={r.refund} reason="Not refunded yet" /></span>
                      {cost && <span className="rows__sub">Return cost <Figure amount={cost} /></span>}
                    </span>
                  </li>
                );
              }))}
            </ul>
          </div>
        </>
      )}
    </section>
  );
}
