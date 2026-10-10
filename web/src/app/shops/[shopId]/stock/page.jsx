/**
 * S7 Stock. What is on hand for each variant, its state and its days of cover.
 *
 * The state and days of cover are computed by `getStock` (service/app/stock.py) and shown as
 * they arrive. The labels are A8's: stock on hand, sold not yet dispatched, returns in
 * transit, stock written off and days of cover.
 *
 * Since 10 October 2026 (A36 step 6, the brief's section 15) the page opens with the
 * shop's totals, units in hand, sold but not posted, coming back and written off, and what
 * runs out first. `getStock` serves both on its first page for the whole shop, so nothing is
 * added up or ordered here (A29.1). The brief's "profit contribution" is not on this page,
 * because no stock figure here is costed, so its "add costs" line has nothing to qualify.
 */

import Link from "next/link";
import { fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { STOCK_STATE, chipClass } from "@/lib/terms";

export const metadata = { title: "Stock" };

const FILTERS = [
  ["", "All"],
  ["out", "Out of stock"],
  ["low", "Low"],
  ["coming_back", "Returns in transit"],
  ["healthy", "Healthy"],
];

/**
 * @param {{
 *   params: Promise<{ shopId: string }>,
 *   searchParams: Promise<Record<string, string>>,
 * }} props
 */
export default async function StockPage({ params, searchParams }) {
  const { shopId } = await params;
  const query = await searchParams;
  const state = query.state ?? "";

  const result = await fetchShop(shopId, "/stock", { state, cursor: query.cursor });
  const problem = apiProblem(result, { what: "your stock" });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["StockPosition"][]} */
  const items = result.data.items ?? [];
  const { as_of, next_cursor, totals, runs_out_first: runsOut } = result.data;
  const base = `/shops/${shopId}/stock`;

  return (
    <section>
      <header className="page-head">
        <h1>Stock</h1>
        <p>Know what is on hand, what is coming back and what may run out next.</p>
        <p className="muted">
          This is your stock as TikTok last reported it, with your own adjustments.
          {items.length > 0 && ` The newest count is from ${formatDate(as_of, { time: true })}.`}
        </p>
      </header>

      {totals && (
        <div className="card" data-testid="stock-totals">
          <h2>Units in hand</h2>
          <ul className="rows">
            <li><span>Units in hand</span><strong className="money">{totals.on_shelf}</strong></li>
            <li><span>Sold but not posted</span><strong className="money">{totals.sold_not_posted}</strong></li>
            <li><span>Coming back</span><strong className="money">{totals.coming_back}</strong></li>
            <li><span>Written off</span><strong className="money">{totals.written_off}</strong></li>
          </ul>
          {totals.coming_back > 0 && (
            <p className="card__foot"><Link href={`/shops/${shopId}/returns`} data-testid="returns-link">Check returns</Link></p>
          )}
        </div>
      )}

      {runsOut && runsOut.length > 0 && (
        <div className="card" data-testid="stock-runs-out">
          <h2>What runs out first</h2>
          <ul className="rows">
            {runsOut.map((/** @type {import("@/lib/api-types").components["schemas"]["StockPosition"]} */ s) => (
              <li key={s.sku_id}>
                <Link href={`${base}/${s.sku_id}`}>{s.product_title || "Untitled product"}</Link>
                <strong>
                  {s.days_left} {s.days_left === 1 ? "day" : "days"} of cover, {s.on_shelf} on hand
                </strong>
              </li>
            ))}
          </ul>
        </div>
      )}

      <nav className="switch" aria-label="Show">
        {FILTERS.map(([value, label]) => (
          <Link
            key={value || "all"}
            href={value ? `${base}?state=${value}` : base}
            aria-current={state === value ? "true" : undefined}
          >
            {label}
          </Link>
        ))}
      </nav>

      {items.length === 0 ? (
        <section className="state">
          <h2>{state ? "No variants in this state." : "No stock recorded yet."}</h2>
          <p>
            {state
              ? "Nothing matches this filter right now."
              : "Stock appears here once the first sync brings in your products."}
          </p>
        </section>
      ) : (
        <div className="card">
          <p className="rows__sub" style={{ marginTop: 0 }}>
            Days of cover is stock on hand divided by the daily rate of the last fourteen days.
            It is not shown when nothing sold in that time. Low means fewer days of cover than
            your <Link href={`/shops/${shopId}/settings/alerts`}>low stock alert</Link>, which is
            fourteen days unless you change it.
          </p>
          <ul className="rows">
            {items.map((s) => {
              const [label, tone] = STOCK_STATE[s.state] ?? [s.state, "quiet"];
              return (
                <li key={s.sku_id}>
                  <span>
                    <Link href={`${base}/${s.sku_id}`}>{s.product_title || "Untitled product"}</Link>
                    <span className="rows__sub"> {s.seller_sku ?? "No seller SKU"}</span>
                    <div className="rows__sub">
                      {s.on_shelf} on hand
                      {s.days_left != null ? `, ${s.days_left} ${s.days_left === 1 ? "day" : "days"} of cover` : ""}
                      {s.sold_not_posted ? `. ${s.sold_not_posted} sold, not yet dispatched` : ""}
                      {s.coming_back ? `. ${s.coming_back} returns in transit` : ""}
                      {s.written_off ? `. ${s.written_off} written off` : ""}
                      .
                    </div>
                  </span>
                  <span className={chipClass(tone)}>{label}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {next_cursor && (
        <p className="pager">
          <Link
            className="btn btn--quiet"
            href={`${base}?${new URLSearchParams({ ...(state ? { state } : {}), cursor: next_cursor })}`}
          >
            Next page
          </Link>
        </p>
      )}
    </section>
  );
}
