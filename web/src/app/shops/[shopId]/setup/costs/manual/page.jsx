/**
 * S20 Manual cost entry (A3). Built 29 September 2026 on listSkuCosts, added to the contract
 * for it, and putSkuCost. Rows are ordered by units sold in the last 30 days, so the products
 * that matter most are typed first. The coverage line is the service's getCostCoverage, not
 * a count made here, and it moves when the page refreshes after a save.
 */

import Link from "next/link";
import { fetchShop } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { ManualCosts } from "@/components/SetupForms";

export const metadata = { title: "Type your costs" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function ManualCostsPage({ params }) {
  const { shopId } = await params;
  const [costs, coverage] = await Promise.all([fetchShop(shopId, "/costs"), fetchShop(shopId, "/costs/coverage")]);
  const problem = apiProblem(costs, { what: "your products" });
  if (problem) return problem;
  /** @type {any[]} */
  const skus = costs.data.skus ?? [];
  const currency = skus.find((s) => s.cost)?.cost?.currency ?? "GBP";
  const rows = skus.map((s) => ({
    sku_id: s.sku_id,
    title: [s.product_title, s.variant_label].filter(Boolean).join(", ") || "A product TikTok did not name",
    seller_sku: s.seller_sku, units: s.units_30d, has_cost: !!s.cost,
  }));

  return (
    <section data-testid="manual-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/setup/costs`}>Product costs</Link></p>
        <h1>Type your costs</h1>
        <p>Product cost is needed. Packing and postage are optional.</p>
      </header>
      {coverage.ok && (
        <p className="note" data-testid="coverage-line">
          {coverage.data.units_with_cost} of {coverage.data.units_total} units sold this month have a cost
          ({Math.round(coverage.data.coverage * 100)}%).
        </p>
      )}
      {rows.length === 0
        ? <p className="muted">Your shop's products appear here once the first sync has read them.</p>
        : <ManualCosts shopId={shopId} rows={rows} currency={currency} />}
    </section>
  );
}
