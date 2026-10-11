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
 * **The brief's table**, since 10 October 2026 (A36 step 6, section 13): product, units sold,
 * net sales, TikTok deductions, product cost, return impact, gross profit after returns, gross
 * margin and cost status, each served by `listProducts`. Starter's table stops at net
 * proceeds. A product whose cost status is not complete links to its page to add the cost.
 *
 * **A37 phase 4, 11 October 2026.** The table showed nine columns and was clipped at 1280 px,
 * with Gross profit after returns, the column that matters, cut off, and on a phone two
 * figures showed before the rest scrolled out of sight. On a larger screen the table now
 * has six columns: units sold and returned, and the cost status, sit under the product's
 * name, and the margin sits under its gross profit. On a phone each product is one row with
 * its gross profit and margin, and its page holds the rest. Every figure is still the
 * service's; only where each sits has changed.
 *
 * **Starter ranks by net proceeds** (the pricing ruling of 10 October 2026). The service
 * answers the default ranking with `measure` net_proceeds and no profit on any row, so the
 * first switch reads Net proceeds, each row shows its net proceeds, and the page carries the
 * ruling's sentence about adding costs with Growth.
 */

import Link from "next/link";
import { api, fetchProducts, formatDate } from "@/lib/api";
import { LockedBlock } from "@/components/Locked";
import { Figure } from "@/components/Figure";
import { apiProblem } from "@/components/ApiProblem";
import { LineLabel } from "@/components/LineLabel";
import { BEFORE_OVERHEADS, chipClass, coverageSentence, formatMargin } from "@/lib/terms";
import { NOT_ON_PLAN } from "@/lib/upgrade";

export const metadata = { title: "Products" };

/** The switch on the sheet, in A8's words. Since A37 phase 4 the first reads Gross profit,
 * which fits a phone's row; the line above the switch names it in full. */
const SWITCH = [
  ["kept", "Gross profit"],
  ["units", "Units"],
  ["returns", "Returns"],
];

/** The brief's cost statuses (section 13), as the service serves them. @type {Record<string, [string, string]>} */
const COST_STATUS = {
  complete: ["Complete", "good"],
  cost_needed: ["Cost needed", "cost"],
  partially_costed: ["Partially costed", "cost"],
  needs_review: ["Needs review", "review"],
};

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

  const [result, subRes] = await Promise.all([
    fetchProducts(shopId, { measure: query.measure, from: query.from, to: query.to }),
    api("/billing/subscription", { cache: "no-store" }),
  ]);
  // A38: Explorer sees gross profit; margin and the rest of Starter's product tools are shown
  // locked under the list. When the plan cannot be read, nothing is shown locked.
  const marginLocked = subRes.ok && !(subRes.data?.features ?? []).includes("margin");
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

  const rows = [...ranked, ...uncosted];
  /** The row's main figure: gross profit after returns, or net proceeds on Starter. @param {ProductRow} p */
  const main = (p) => starter
    ? <Figure amount={p.net_proceeds} />
    : <Figure amount={p.kept} reason={p.kept_reason} />;
  /** Units sold and returned, in a few words. @param {ProductRow} p */
  const units = (p) => `${p.units} sold${p.returns_units ? ` \u00b7 ${p.returns_units} returned` : ""}`;
  /** The cost status chip, a link to the product when its cost is not complete. @param {ProductRow} p */
  const status = (p) => {
    const [word, tone] = COST_STATUS[p.cost_status ?? ""] ?? [null, "quiet"];
    if (!word || starter || p.cost_status === "complete") return null;
    return <Link className={chipClass(tone)} href={`${base}/${p.product_id}`}>{word}</Link>;
  };

  return (
    <section className="overview">
      <header className="page-head">
        <h1>Products</h1>
        <p data-testid="products-measure">{RANKED_BY[measure] ?? "Ranked"}{dates}</p>
      </header>

      <div className="toolbar">
        <nav className="switch switch--compact" aria-label="Rank by">
          {SWITCH_SHOWN.map(([value, label]) => (
            <Link key={value} href={value === "kept" ? base : `${base}?measure=${value}`}
                  aria-current={measure === value || (starter && value === "kept" && measure === "net_proceeds") ? "true" : undefined}>
              {label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Added 30 September 2026: the owner found no way from Products to upload a cost
          file. Costs are what turn sales into gross profit, so the way in sits on this page.
          Since A37 phase 4 it is one line with small buttons. */}
      <div className="card products__costs" data-testid="products-coverage">
        <p className="products__coverage">
          {/* A36: the brief's cost coverage card, from the service's coverage by sales value. */}
          {!coverage
            ? "Product costs not added yet. You can already see net proceeds; add costs to see gross profit by product."
            : coverageSentence(coverage) ?? <><span className="overview__clear"><span aria-hidden="true">{"\u2713"}</span></span>Every product sold has a cost.</>}
          {coverage && coverage.products_missing > 0 && (
            <> <Link href={`/shops/${shopId}/setup/costs/manual`}>Review missing costs</Link></>
          )}
        </p>
        <div className="products__buttons">
          <Link className="btn btn--primary btn--small" href={`/shops/${shopId}/setup/costs/upload`}>Upload costs</Link>
          <Link className="btn btn--quiet btn--small" href={`/shops/${shopId}/setup/costs/manual`}>Type in</Link>
          {/* A36 step 7: the brief's template download, filled with the shop's variants. */}
          <a className="btn btn--quiet btn--small" href={`/shops/${shopId}/setup/costs/template`} data-testid="products-template">Template</a>
        </div>
      </div>

      {products.length === 0 ? (
        <div className="card overview__more">
          <p className="muted">No products sold in this period yet.</p>
        </div>
      ) : (
        <div className="card overview__more">
          {/* The brief's product table (section 13), on a larger screen. Every figure is the
              service's. A product without a full cost shows its cost status and no profit. */}
          <div className="products__table">
            <table data-testid="products-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th className="num">Net sales</th>
                  <th className="num">TikTok deductions</th>
                  {starter ? (
                    <th className="num">Net proceeds</th>
                  ) : (
                    <>
                      <th className="num">Product cost</th>
                      <th className="num">Return impact</th>
                      <th className="num">Gross profit after returns</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.product_id} data-testid="product-row">
                    <td>
                      <Link className="rowlink" href={`${base}/${p.product_id}`}>{p.title || "Untitled product"}</Link>
                      <span className="rows__sub products__sub">{units(p)} {status(p)}</span>
                    </td>
                    <td className="num"><Figure amount={p.net_sales} /></td>
                    <td className="num"><Figure amount={p.tiktok_deductions} /></td>
                    {starter ? (
                      <td className="num products__main">{main(p)}</td>
                    ) : (
                      <>
                        <td className="num"><Figure amount={p.product_cost} reason="Not every variant sold has a cost price." /></td>
                        <td className="num"><Figure amount={p.return_impact} /></td>
                        <td className="num products__main">
                          {main(p)}
                          {formatMargin(p.gross_margin_after_returns) && (
                            <span className="rows__sub products__sub">{formatMargin(p.gross_margin_after_returns)} margin</span>
                          )}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* On a phone, one row per product with its main figure. Its page holds the rest. */}
          <ul className="rows payouts products__list" data-testid="products-list">
            {rows.map((p) => (
              <li key={p.product_id}>
                <Link className="payouts__row" href={`${base}/${p.product_id}`}>
                  <span className="payouts__when">
                    {p.title || "Untitled product"}
                    <span className="rows__sub">{units(p)}</span>
                  </span>
                  <span className="products__figure">
                    {main(p)}
                    {!starter && formatMargin(p.gross_margin_after_returns) && (
                      <span className="rows__sub">{formatMargin(p.gross_margin_after_returns)} margin</span>
                    )}
                    {status(p)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>

          <ul className="rows products__totals">
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
              {total && measure === "kept" ? " Included in the total." : ""}
            </p>
          )}
        </div>
      )}

      {marginLocked && products.length > 0 && (
        <div className="overview__more">
          <LockedBlock plan="starter" testId="products-locked"
            items={["Gross margin by product", "Cost coverage and missing-cost alerts",
                    "Return and write-off profit treatment", "Full order-level drilldown"]} />
        </div>
      )}
      {starter && <p className="footnote overview__note" data-testid="products-not-on-plan">{NOT_ON_PLAN}</p>}
      {measure === "kept" && (
        <p className="footnote overview__note">
          {BEFORE_OVERHEADS}
          {unattributed ? " The shop total matches Where the money went." : ""}
        </p>
      )}
    </section>
  );
}
