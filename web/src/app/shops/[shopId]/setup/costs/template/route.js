/**
 * The cost template, a CSV of every variant in the shop with the cost in force today, for the
 * brief's "Download cost template" (A36 step 7, section 8A). Built 10 October 2026.
 *
 * It reads `listSkuCosts` and lays the answer out as a file; it works nothing out. The
 * columns are the ones the upload recognises without being told: SKU, then the product and
 * variation to help the seller find their place, then the cost per unit and the date it
 * applies from. A variant with no seller SKU carries TikTok's own SKU id in the SKU column,
 * which the upload matches as a fallback. Excel shortens an id that long to fifteen digits
 * unless its column is formatted as text, which the upload page says.
 */

import { api } from "@/lib/api";

/** One CSV field, quoted when it holds a comma, a quote or a line break. @param {unknown} v */
function field(v) {
  const s = v == null ? "" : String(v);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** Pence as pounds with two decimals, the way the upload reads them. @param {number} minor */
function pounds(minor) {
  const sign = minor < 0 ? "-" : "";
  const abs = Math.abs(minor);
  return `${sign}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, "0")}`;
}

/**
 * @param {Request} _request
 * @param {{ params: Promise<{ shopId: string }> }} context
 */
export async function GET(_request, { params }) {
  const { shopId } = await params;
  const r = await api(`/shops/${encodeURIComponent(shopId)}/costs`, { cache: "no-store" });
  if (!r.ok) {
    // Not on a plan with costs, or the list did not load: back to the upload page, which
    // explains either.
    return Response.redirect(new URL(`/shops/${shopId}/setup/costs/upload`, _request.url), 303);
  }
  /** @type {{ seller_sku?: string | null, tiktok_sku_id?: string | null, product_title?: string | null, variant_label?: string | null, cost?: { amount_minor: number } | null }[]} */
  const skus = r.data?.skus ?? [];
  const lines = [["SKU", "Product", "Variation", "Cost per unit", "Effective date"].join(",")];
  for (const s of skus) {
    lines.push([
      field(s.seller_sku || s.tiktok_sku_id || ""),
      field(s.product_title ?? ""),
      field(s.variant_label ?? ""),
      field(s.cost ? pounds(s.cost.amount_minor) : ""),
      "",
    ].join(","));
  }
  return new Response(`${lines.join("\r\n")}\r\n`, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": 'attachment; filename="myshopedge-cost-template.csv"',
      "cache-control": "no-store",
    },
  });
}
