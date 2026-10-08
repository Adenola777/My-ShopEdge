/**
 * S29 Disconnect, bound to disconnectShop (CON-3).
 *
 * Written by Emergent AI in `Adenola777/MYSHOPEDGE` (commit 3f1bd43) and brought into this
 * repository on 28 September 2026 at the owner's instruction. See
 * `audit/EMERGENT_review_28_september.md`.
 */

import Link from "next/link";
import { fetchShop } from "@/lib/api";
import { apiProblem, NOTHING_CHANGED } from "@/components/ApiProblem";
import { DisconnectAction } from "@/components/SettingsForms";

export const metadata = { title: "Disconnect this shop" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function DisconnectPage({ params }) {
  const { shopId } = await params;
  // A read that proves the shop is the caller's before the page offers to disconnect it.
  const result = await fetchShop(shopId, "/alert-settings");
  const problem = apiProblem(result, { what: "this shop", note: NOTHING_CHANGED });
  if (problem) return problem;

  return (
    <section data-testid="disconnect-screen">
      <header className="page-head">
        <h1>Disconnect this shop</h1>
        <p>MyShopEdge stops reading from TikTok. Nothing you already have is deleted. Disconnecting does not change your plan, and you can stop it renewing in <Link href={`/shops/${shopId}/settings/profile`}>Profile and plan</Link>.</p>
      </header>
      <div className="card">
        <h2>What stays</h2>
        <ul className="rows">
          <li><span>Your orders, returns and settlements</span><strong>Kept</strong></li>
          <li><span>Your ledger and figures</span><strong>Kept</strong></li>
          <li><span>Your product costs</span><strong>Kept</strong></li>
        </ul>
        <p className="card__why">If you connect the same shop again later, MyShopEdge reads from where it stopped and adds what you missed to these records. MyShopEdge does not ask TikTok to withdraw the approval you gave it.</p>
      </div>
      <DisconnectAction shopId={shopId} />
    </section>
  );
}
