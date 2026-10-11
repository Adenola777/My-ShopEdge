/**
 * S10 Product detail. Whether one product makes money.
 *
 * `getProduct` serves the calculator for the product over the period, the same calculator
 * per unit, the stock position, and each variant with its cost. The screen lays them out
 * and computes nothing. A18.2 requires the screen to say that the figures are allocated,
 * because TikTok reports deductions per order, not per product.
 *
 * Drawn to wireframe sheet 06 (redrawn 24 September after the design audit): the title
 * with the SKU and the count on the shelf, one unit pound by pound, the figures for the
 * period, then the variants with their costs.
 *
 * Not yet as the sheet shows. The segmented bar across one unit waits for the per product
 * split that phase 3 of the audit adds to the contract. "Worth a look" is not served by
 * anything. The Returns card needs a product's return rate, which the contract does not
 * carry. None of these is drawn empty.
 *
 * **A37 phase 4, 11 October 2026.** The main figure comes first, and the period's figures and
 * one unit's figures are one table with a column for each, where they had been two cards of
 * the same lines. `getProduct` builds `per_unit` from the period's sections line for line
 * (products.py), so the two line up by position. The explanations are shortened (A37.1 item 9).
 *
 * A cost is set per variant through `putSkuCost` (S21). The stock count appears only for a
 * product with a single variant, which is what the service serves (products.py says why).
 */

import Link from "next/link";
import { fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { CostForm } from "@/components/CostForm";
import { Figure } from "@/components/Figure";
import { LineLabel } from "@/components/LineLabel";
import { BEFORE_OVERHEADS, STOCK_STATE, chipClass, formatMargin } from "@/lib/terms";

/** The brief's cost statuses as chips, shown beside the main figure unless complete. @type {Record<string, [string, string]>} */
const COST_CHIP = {
  cost_needed: ["Cost needed", "cost"],
  partially_costed: ["Partially costed", "cost"],
  needs_review: ["Needs review", "review"],
};

export const metadata = { title: "Product" };

/**
 * @param {{
 *   params: Promise<{ shopId: string, productId: string }>,
 *   searchParams: Promise<Record<string, string>>,
 * }} props
 */
export default async function ProductDetailPage({ params, searchParams }) {
  const { shopId, productId } = await params;
  const query = await searchParams;

  const result = await fetchShop(shopId, `/products/${encodeURIComponent(productId)}`, {
    basis: query.basis,
    from: query.from,
    to: query.to,
  });
  const problem = apiProblem(result, {
    what: "this product",
    notFound: "That product was not found.",
  });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["ProductDetail"]} */
  const d = result.data;
  const p = d.product;
  const perUnit = /** @type {{ units: number, sections: any[] }} */ (d.per_unit);
  const stock = d.stock;
  const [stateLabel, stateTone] = stock
    ? (STOCK_STATE[stock.state] ?? [stock.state, "quiet"])
    : ["", "quiet"];

  const sections = /** @type {any[]} */ (d.sections);
  const period = /** @type {{ from?: string, to?: string, basis?: string } | undefined} */ (d.period);
  const periodWords = period?.from && period?.to
    ? `${formatDate(period.from)} to ${formatDate(period.to)}`
    : "This period";
  const recordsQuery = new URLSearchParams({
    ...(period?.from ? { from: period.from } : {}),
    ...(period?.to ? { to: period.to } : {}),
    ...(period?.basis ? { basis: period.basis } : {}),
  }).toString();
  const transactionsHref = `/shops/${shopId}/products/${productId}/transactions${recordsQuery ? `?${recordsQuery}` : ""}`;
  const [costWord, costTone] = COST_CHIP[p.cost_status ?? ""] ?? [null, "quiet"];
  const margin = formatMargin(p.gross_margin_after_returns);

  return (
    <section className="overview">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/products`}>Products</Link></p>
        <h1>{p.title || "Untitled product"}</h1>
        <p>
          {p.units} sold {"\u00b7"} {periodWords}
          {stock ? <> {"\u00b7"} {stock.on_shelf} in stock <span className={chipClass(stateTone)}>{stateLabel}</span></> : null}
        </p>
      </header>

      <div className="card hero">
        <p className="hero__label">
          Gross profit after returns{" "}
          {costWord && <span className={chipClass(costTone)}>{costWord}</span>}
        </p>
        <p className="hero__value"><Figure amount={p.kept} reason={p.kept_reason} /></p>
        {!p.kept && p.kept_reason && <p className="hero__line">{p.kept_reason}</p>}
        <p className="hero__meta">
          {margin && <span data-testid="product-margin"><strong>{margin}</strong> margin</span>}
          {/* A36 step 6: net proceeds sits with the headline, as the brief's product detail lists it. */}
          <span data-testid="product-net-proceeds">Net proceeds <Figure amount={p.net_proceeds} /></span>
          <span>All {p.units} {p.units === 1 ? "unit" : "units"}</span>
        </p>
        <p className="hero__action"><Link data-testid="product-transactions-link" href={transactionsHref}>See the orders behind these figures</Link></p>
      </div>

      <h2 className="overview__heading">Where the money went</h2>
      <div className="card statement">
        {sections.length === 0 ? (
          <p className="muted">No sales of this product in this period.</p>
        ) : (
          <table className="unit-table" data-testid="per-unit">
            <thead>
              <tr><th><span className="visually-hidden">Line</span></th><th className="num">Total</th><th className="num">Per unit</th></tr>
            </thead>
            {sections.map((sec, si) => {
              const unit = perUnit.sections[si];
              return (
                <tbody key={sec.key}>
                  {sec.lines.map((/** @type {any} */ l, /** @type {number} */ i) => (
                    <tr key={`${sec.key}-${l.category}-${i}`}>
                      <td><LineLabel line={l} /></td>
                      <td className="num"><Figure amount={l.amount} alert={l.category === "stock_written_off"} /></td>
                      <td className="num">{unit?.lines[i] ? <Figure amount={unit.lines[i].amount} alert={l.category === "stock_written_off"} /> : null}</td>
                    </tr>
                  ))}
                  <tr className="unit-table__total">
                    <td>{sec.subtotal_label ?? "Subtotal"}</td>
                    <td className="num"><Figure amount={sec.subtotal} /></td>
                    <td className="num">{unit ? <Figure amount={unit.subtotal} /> : null}</td>
                  </tr>
                </tbody>
              );
            })}
          </table>
        )}
      </div>
      {sections.length > 0 && (
        <p className="footnote overview__note">
          Per unit is the total over {perUnit.units} {perUnit.units === 1 ? "unit" : "units"}, rounded to the penny.
          Deductions TikTok reports per order are shared across its products in proportion.
          {p.kept ? ` ${BEFORE_OVERHEADS}` : ""}
        </p>
      )}

      {p.cost_status === "needs_review" && (
        <div className="note note--warn overview__more" data-testid="cost-needs-review">
          <p>
            Your latest cost file disagrees with the cost set here, so it was not applied. Upload
            it again or set the cost below.{" "}
            <Link href={`/shops/${shopId}/setup/costs/upload`}>Upload costs</Link>
          </p>
        </div>
      )}

      <h2 className="overview__heading" id="edit-cost">Product cost</h2>
      <div className="card">
        <p className="card__why">Cost of one unit. Applies to units sold from the date chosen, until a later cost takes over.</p>
        <ul className="rows">
          {(d.skus ?? []).map((s) => (
            <li key={s.sku_id} style={{ flexWrap: "wrap" }}>
              <span>
                <Link className="rowlink" href={`/shops/${shopId}/stock/${s.sku_id}`}>
                  {s.variant_label || s.seller_sku || "Variant"}
                </Link>
                <span className="rows__sub" style={{ display: "block" }}>
                  {s.seller_sku ?? "No seller SKU"}
                </span>
              </span>
              <Figure amount={s.cost} reason="Not provided" />
              {s.sku_id && (
                <div style={{ flexBasis: "100%" }}>
                  <CostForm shopId={shopId} skuId={s.sku_id}
                            variantName={s.variant_label || s.seller_sku || p.title || undefined}
                            currency={s.cost?.currency ?? p.gross_sales.currency ?? "GBP"} />
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
