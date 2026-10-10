/**
 * S2 First sync, bound to getSyncStatus (SYN-1). Drawn to wireframe sheet 02.
 *
 * Emergent AI wrote the first version in `Adenola777/MYSHOPEDGE` (commit 3f1bd43); it was
 * brought in on 28 September 2026 with its progress card rewritten (see `SyncProgress`).
 *
 * Two parts of the sheet are left out. "Orders, last 12 months" is out of date, because
 * history is twenty four months on every plan, so the row says "Orders and sales" and no
 * period. A14.2 puts S33 Plan and card next, so a seller with no plan continues there.
 * After that the sheet's "Continue to product costs" leads to S3, which is not built, so the
 * button leads to Products, where a cost is added to each variant today.
 */

import Link from "next/link";
import { api, fetchShop } from "@/lib/api";
import { importSteps } from "@/lib/onboarding";
import { afterSync } from "@/lib/onboarding";
import { apiProblem } from "@/components/ApiProblem";
import { SyncProgress } from "@/components/SyncProgress";

export const metadata = { title: "We are putting your figures together" };

/** @param {{ params: Promise<{ shopId: string }>, searchParams: Promise<{ connected?: string }> }} props */
export default async function SyncPage({ params, searchParams }) {
  const { shopId } = await params;
  const { connected } = await searchParams;
  const [result, sub, shopsRes] = await Promise.all([
    fetchShop(shopId, "/sync"),
    api("/billing/subscription", { cache: "no-store" }),
    connected ? api("/shops", { cache: "no-store" }) : Promise.resolve(null),
  ]);
  const problem = apiProblem(result, { what: "your sync status" });
  if (problem) return problem;
  const status = sub.ok ? sub.data?.status ?? null : null;
  /** @type {{ id: string, shop_name?: string | null } | undefined} */
  const shop = shopsRes?.ok ? (shopsRes.data?.shops ?? []).find((/** @type {any} */ s) => s.id === shopId) : undefined;
  const steps = importSteps(result.data?.domains ?? []);

  // The brief's section 5, approved under A36: one heading, four plain steps, no percentage,
  // and no request for product costs while the import runs.
  return (
    <section data-testid="sync-screen">
      {connected && (
        <p className="note" role="status" data-testid="sync-connected">
          {shop?.shop_name ?? "Your shop"} is connected. MyShopEdge only reads your shop and never changes it.
        </p>
      )}
      <header className="page-head">
        <h1>We are putting your figures together.</h1>
        <p>We are securely reading your available orders, fees, refunds, returns, settlements and payouts.</p>
      </header>
      <div className="stack">
        <div className="card" data-testid="import-steps">
          <ul className="rows">
            {steps.map(([label, state]) => (
              <li key={label}>
                <span>{label}</span>
                <span className={state === "done" ? "chip chip--good" : state === "now" ? "chip chip--warn" : "chip chip--quiet"}>
                  {state === "done" ? "Done" : state === "now" ? "In progress" : "Waiting"}
                </span>
              </li>
            ))}
          </ul>
          <p className="card__why">We will show your first results as soon as they are ready.</p>
        </div>
        {status === "none" && (
          <p className="card__why">We are preparing your shop figures while you choose your plan.</p>
        )}
        <p>
          <Link className="btn btn--primary btn--block" href={afterSync(shopId, status)} data-testid="sync-continue">
            {status === "none" ? "Choose your plan" : "See my first results"}
          </Link>
        </p>
        <details>
          <summary>What has been read so far</summary>
          <SyncProgress shopId={shopId} initial={result.data} />
        </details>
      </div>
    </section>
  );
}
