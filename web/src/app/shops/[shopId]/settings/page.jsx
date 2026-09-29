/**
 * S15 Settings and data, drawn to wireframe sheet 09. It is reached from the top bar.
 *
 * Emergent AI wrote a hub of links in `Adenola777/MYSHOPEDGE` (commit 3f1bd43). On 28
 * September 2026 it was redrawn to the sheet's three cards, and every value on it is read
 * from the service: the connection from listShops, the tax profile from getTaxProfile, the
 * low stock threshold from getAlertSettings and the missing costs from getCostCoverage. A
 * value whose request fails is shown as not available rather than guessed.
 *
 * Left out of the sheet: the export and the data download in the "Your data" card, because
 * neither is built. Emergent's version offered deletion and told the seller their data was
 * erased when nothing was. Deletion was built on 28 September to A30.1 and is linked at the
 * foot as S30. The privacy notice sentence is left out because the notice does not exist.
 */

import Link from "next/link";
import { api, fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { chipClass } from "@/lib/terms";

export const metadata = { title: "Settings and data" };

/** @type {Record<string, [string, string]>} */
const CONNECTION = {
  connected: ["Connected", "good"],
  pending: ["Being read", "warn"],
  needs_reconnect: ["Reconnect needed", "critical"],
  disconnected: ["Disconnected", "critical"],
};

/** @type {Record<string, string>} */
const STRUCTURE = {
  sole_trader: "Sole trader",
  company: "Limited company",
  not_sure: "Not sure yet",
};

/**
 * getCostCoverage covers this month to date by default, so a month with no sales yet says so
 * rather than claiming every variant is costed.
 *
 * @param {import("@/lib/api-types").components["schemas"]["CostCoverage"]} c
 */
function costWords(c) {
  if (c.units_total === 0) return "No sales yet this month";
  if (c.skus_missing_cost === 0) return "Every variant sold this month has a cost";
  return `${c.skus_missing_cost} ${c.skus_missing_cost === 1 ? "variant" : "variants"} sold this month without a cost`;
}

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function SettingsPage({ params }) {
  const { shopId } = await params;
  const base = `/shops/${shopId}`;
  const [shopsRes, taxRes, alertsRes, coverageRes] = await Promise.all([
    api("/shops", { cache: "no-store" }),
    api("/tax-profile", { cache: "no-store" }),
    fetchShop(shopId, "/alert-settings"),
    fetchShop(shopId, "/costs/coverage"),
  ]);
  const problem = apiProblem(shopsRes, { what: "your settings" });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["Shop"][]} */
  const shops = shopsRes.data?.shops ?? [];
  const shop = shops.find((s) => s.id === shopId);
  const [statusLabel, statusTone] = shop ? (CONNECTION[shop.connection_status] ?? [shop.connection_status, "quiet"]) : ["Not known", "quiet"];
  const healthy = shop?.connection_status === "connected";

  const tax = taxRes.ok ? taxRes.data : null;
  const alerts = alertsRes.ok ? alertsRes.data : null;
  const coverage = coverageRes.ok ? coverageRes.data : null;
  const unavailable = <span className="muted">Not available</span>;

  return (
    <section data-testid="settings-page">
      <header className="page-head">
        <h1>Settings and data</h1>
      </header>
      <div className="stack">
        <div className="card" data-testid="settings-connection">
          <h2>TikTok Shop connection</h2>
          <ul className="rows">
            <li>
              <span>Status</span>
              {healthy ? (
                <span className={chipClass(statusTone)}>{statusLabel}</span>
              ) : (
                <Link href={`${base}/connection-problem`} className={chipClass(statusTone)}>{statusLabel}</Link>
              )}
            </li>
            <li>
              <span>Last updated</span>
              <strong>{shop?.last_synced_at ? formatDate(shop.last_synced_at, { time: true }) : "Not yet"}</strong>
            </li>
            <li><span>Access</span><strong>Read-only</strong></li>
            <li>
              <span><Link href={`${base}/sync`}>What has been read</Link></span>
            </li>
          </ul>
        </div>

        <div className="card" data-testid="settings-setup">
          <h2>Your set-up</h2>
          <ul className="rows">
            <li>
              <span><Link href={`${base}/products`}>Product costs</Link></span>
              {coverage ? <strong>{costWords(coverage)}</strong> : unavailable}
            </li>
            <li>
              <span>Tax profile</span>
              {tax
                ? <strong>{tax.completed && tax.business_structure ? (STRUCTURE[tax.business_structure] ?? tax.business_structure) : "Not filled in"}</strong>
                : unavailable}
            </li>
            <li>
              <span><Link href={`${base}/settings/alerts`}>Low stock alert</Link></span>
              {alerts ? <strong>{alerts.low_stock_days} days</strong> : unavailable}
            </li>
            <li>
              <span><Link href={`${base}/other-sales`}>Other-channel sales</Link></span>
            </li>
            <li>
              <span><Link href={`${base}/glossary`}>Glossary</Link></span>
            </li>
          </ul>
        </div>

        <p>
          <Link className="btn btn--quiet btn--block" href={`${base}/settings/disconnect`} data-testid="settings-disconnect">
            Disconnect TikTok Shop
          </Link>
        </p>
        <p className="footnote">Disconnecting stops updates. Nothing you already have is deleted.</p>
        <p>
          <Link className="btn btn--quiet btn--block" href={`${base}/settings/data`} data-testid="settings-data">
            Download my data
          </Link>
        </p>
        <p>
          <Link className="btn btn--quiet btn--block" href={`${base}/settings/delete`} data-testid="settings-delete">
            Delete my account
          </Link>
        </p>
      </div>
    </section>
  );
}
