/**
 * S2 First sync, bound to getSyncStatus (SYN-1). Drawn to wireframe sheet 02.
 *
 * Emergent AI wrote the first version in `Adenola777/MYSHOPEDGE` (commit 3f1bd43); it was
 * brought in on 28 September 2026 with its progress card rewritten (see `SyncProgress`).
 *
 * Two parts of the sheet are left out. "Orders, last 12 months" is out of date, because
 * history is twenty four months on every plan, so the row says "Orders and sales" and no
 * period. "Continue to product costs" leads to S3, which is not built, so the button leads
 * to Products, where a cost is added to each variant today.
 */

import Link from "next/link";
import { fetchShop } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { SyncProgress } from "@/components/SyncProgress";

export const metadata = { title: "Getting your shop ready" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function SyncPage({ params }) {
  const { shopId } = await params;
  const result = await fetchShop(shopId, "/sync");
  const problem = apiProblem(result, { what: "your sync status" });
  if (problem) return problem;

  return (
    <section data-testid="sync-screen">
      <header className="page-head">
        <h1>Getting your shop ready</h1>
        <p>This can take a few minutes. You can leave this screen.</p>
      </header>
      <div className="stack">
        <SyncProgress shopId={shopId} initial={result.data} />
        <p>
          <Link className="btn btn--primary btn--block" href={`/shops/${shopId}/products`}>
            Continue to your products
          </Link>
        </p>
      </div>
    </section>
  );
}
