/**
 * S9 Products, drawn to wireframe sheet 06 (redrawn 24 September after the design audit).
 *
 * The sheet: the title and what the ranking is by; a measure switch; one row per product
 * with its figure on the right; uncosted products below the ranked ones with "Add cost".
 *
 * The measure switch is served, because `listProducts` takes `measure`. The ranking comes
 * from the service in its order (A29.1). Uncosted products are listed after the ranked
 * ones, as the sheet shows, by the `cost_known` flag the service returns.
 *
 * **Not yet as the sheet shows.** Each row on the sheet carries a pence-in-the-pound bar
 * split into stock, postage, TikTok and what is left. That split is a financial rule, so it
 * belongs in the service and waits for phase 3 of the audit, which adds it to the contract.
 *
 * A product with no cost shows no profit, never £0.00: `Figure` renders the reason.
 *
 * **Money tied to no product has its own line**, as the owner ruled on 25 September 2026.
 * A platform adjustment TikTok applies to a whole statement belongs to the shop and to no
 * product, so the products alone do not add up to Money. The service returns those lines
 * as `unattributed` and the sum as `shop_total`, and the screen shows both beneath the
 * products, so the last figure on this screen is the one Money shows for the same period.
 *
 * **Starter ranks by net proceeds** (the pricing ruling of 10 October 2026). The service
 * answers the default ranking with `measure` net_proceeds and no profit on any row, so the
 * first switch reads Net proceeds, each row shows its net proceeds, and the page carries the
 * ruling's sentence about adding costs with Growth.
 */

import Link from "next/link";
import { fetchProducts, formatDate } from "@/lib/api";
import { Figure } from "@/components/Figure";
import { apiProblem } from "@/components/ApiProblem";
import { LineLabel } from "@/components/LineLabel";
import { BEFORE_OVERHEADS, coverageSentence, formatMargin } from "@/lib/terms";
import { NOT_ON_PLAN } from "@/lib/upgrade";

export const metadata = { title: "Products" };

/** The switch on the sheet, in A8's words. */
const SWITCH = [
  ["kept", "Gross profit after returns"],
  ["units", "Units"],
  ["returns", "Returns"],
];

/** @type {Record<string, string>} */
const RANKED_BY = {
  kept: "Ranked by gross profit after returns",
  net_proceeds: "Ranked by net proceeds",
  gross_sales: "Ranked by gross sales",
  units: "Ranked by units sold",
  returns: "Ranked by units returned",
};

/** @param {{ params: Promise<{ shopId: string }>, searchParams: Promise<Record<string,string>> }} props */
export default async function ProductsPage({ params, searchParams }) {
  const { shopId } = await params;
  const query = await searchParams;

  const result = await fetchProducts(shopId, { measure: query.measure, from: query.from, to: query.to });
  const problem = apiProblem(result, { what: "your products" });
  if (problem) return problem;

  /** @typedef {import("@/lib/api-types").components["schemas"]["ProductRow"]} ProductRow */
  /** @typedef {import("@/lib/api-types").components["schemas"]["ProductRanking"]} Ranking */
  /** @type {{ products: ProductRow[], total?: any, measure?: string, others?: { count: number, amount: any }, unattributed?: Ranking["unattributed"], shop_total?: any }} */
  const { products = [], total, measure = "kept", others, unattributed, shop_total } = result.data;
  const coverage = result.data.coverage ?? null;
  /** @type {{ from?: string, to?: string } | undefined} */
  const period = result.data.period;
  const dates = period?.from && period?.to ? `, ${formatDate(period.from)} to ${formatDate(period.to)}` : "";
  /** @type {Record<string, string>} */
  const FIGURE_NAME = {
    kept: "Gross profit after returns",
    units: "Units sold",
    returns: "Units returned",
  };
  const base = `/shops/${shopId}/products`;
  const starter = products.some((p) => p.kept_reason === NOT_ON_PLAN) || (measure === "net_proceeds" && !query.measure);
  const SWITCH_SHOWN = starter ? [["kept", "Net proceeds"], ...SWITCH.slice(1)] : SWITCH;

  const ranked = products.filter((p) => p.cost_known || measure !== "kept");
  const uncosted = measure === "kept" ? products.filter((p) => !p.cost_known) : [];

  return (
    <section>
      <header className="page-head">
        <h1>Products</h1>
        <p>{RANKED_BY[measure] ?? "Ranked"}{dates}.</p>
      </header>

      <nav className="switch" aria-label="Rank by">
        {SWITCH_SHOWN.map(([value, label]) => (
          <Link key={value} href={value === "kept" ? base : `${base}?measure=${value}`}
                aria-current={measure === value || (starter && value === "kept" && measure === "net_proceeds") ? "true" : undefined}>
            {label}
          </Link>
        ))}
      </nav>

      {/* Added 30 September 2026: the owner found no way from Products to upload a cost
          file. Costs are what turn sales into gross profit, so the way in sits on this page. */}
      <div className="card card--action" data-testid="products-coverage">
        <div>
          <h2>{coverage ? "Cost coverage" : "Product costs"}</h2>
          <p className="card__why">
            {/* A36: the brief's cost coverage card, from the service's coverage by sales value. */}
            {!coverage
              ? "Gross profit needs what each product costs you. Upload an Excel or CSV file, or type costs in one by one."
              : coverageSentence(coverage) ?? "Every product sold in this period has a cost."}
          </p>
          {coverage && coverage.products_missing > 0 && (
            <p><Link href={`/shops/${shopId}/setup/costs/manual`}>Review missing costs</Link></p>
          )}
        </div>
        <div className="card--action__buttons">
          <Link className="btn btn--primary" href={`/shops/${shopId}/setup/costs/upload`}>Upload a cost file</Link>
          <Link className="btn btn--quiet" href={`/shops/${shopId}/setup/costs/manual`}>Type costs in</Link>
        </div>
      </div>

      {products.length === 0 ? (
        <section className="state">
          <h2>No products sold in this period yet.</h2>
          <p>Once orders come through, every product you sell appears here, ranked.</p>
        </section>
      ) : (
        <div className="card">
          <ul className="rows rows--products">
            {ranked.map((p) => (
              <li key={p.product_id}>
                <span>
                  <Link className="rowlink" href={`${base}/${p.product_id}`}>
                    {p.title || "Untitled product"}
                  </Link>
                  <div className="rows__sub">
                    {p.units} sold{p.returns_units ? `, ${p.returns_units} returned` : ""}
                    {measure !== "net_proceeds" && <>. Net proceeds{" "}<Figure amount={p.net_proceeds} /></>}
                    {formatMargin(p.gross_margin_after_returns) && <>. Gross margin {formatMargin(p.gross_margin_after_returns)}</>}
                  </div>
                </span>
                <span>
                  <span className="visually-hidden">{FIGURE_NAME[measure] ?? "Figure"}: </span>
                  {measure === "units" ? <strong className="money">{p.units}</strong>
                    : measure === "returns" ? <strong className="money">{p.returns_units || 0}</strong>
                    : measure === "net_proceeds" ? <Figure amount={p.net_proceeds} />
                    : measure === "gross_sales" ? <Figure amount={p.gross_sales} />
                    : <Figure amount={p.kept} reason={p.kept_reason} />}
                </span>
              </li>
            ))}
            {uncosted.map((p) => (
              <li key={p.product_id}>
                <span>
                  <Link className="rowlink" href={`${base}/${p.product_id}`}>
                    {p.title || "Untitled product"}
                  </Link>
                  <div className="rows__sub">
                    This product has no cost price for some of its sales in this period. Its net
                    proceeds are <Figure amount={p.net_proceeds} />.
                  </div>
                </span>
                <Link className="chip chip--strong" href={`${base}/${p.product_id}`}>Add cost</Link>
              </li>
            ))}
            {total && measure === "kept" && (
              <li className="rows__total">
                <span>{unattributed ? "Total across products" : "Total gross profit after returns"}</span>
                <Figure amount={total} />
              </li>
            )}
            {unattributed && measure === "kept" && (
              <>
                <li className="rows__group"><span>For the whole shop, not one product</span></li>
                {unattributed.lines.map((l) => (
                  <li key={`${l.category}-${l.tiktok_fee_type ?? ""}`}>
                    <LineLabel line={l} />
                    <Figure amount={l.amount} />
                  </li>
                ))}
                <li className="rows__total">
                  <span>Total for the shop</span>
                  <Figure amount={shop_total} reason="Not known until every product sold has a cost price." />
                </li>
              </>
            )}
          </ul>
          {others && others.count > 0 && (
            <p className="rows__sub" style={{ marginTop: "var(--space-2)" }}>
              {others.count} more {others.count === 1 ? "product came" : "products came"} to{" "}
              <Figure amount={others.amount} />{others.count === 1 ? "." : " between them."}
              {total && measure === "kept" ? " The total above includes them." : ""}
            </p>
          )}
        </div>
      )}

      {starter && <p className="footnote" data-testid="products-not-on-plan">{NOT_ON_PLAN}</p>}
      {measure === "kept" && (
        <p className="footnote">
          {BEFORE_OVERHEADS}
          {unattributed ? " The total for the shop is the figure Where the money went shows for the same period." : ""}
        </p>
      )}
    </section>
  );
}
