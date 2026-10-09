/**
 * S29 Disconnect, bound to disconnectShop (CON-3).
 *
 * Written by Emergent AI in `Adenola777/MYSHOPEDGE` (commit 3f1bd43) and brought into this
 * repository on 28 September 2026 at the owner's instruction. See
 * `audit/EMERGENT_review_28_september.md`.
 *
 * Since 9 October 2026 the page reads the shop from listShops, which returns only this
 * account's shops, so the same read proves the shop is the caller's and gives its
 * `connection_status`. A shop that is already disconnected is told so and offered the
 * connect button S1 and S28 use, because disconnectShop on it would change nothing the
 * seller could see. Until then the page read alert settings only to prove ownership, and
 * offered to disconnect a shop whatever its state.
 */

import Link from "next/link";
import { api } from "@/lib/api";
import { apiProblem, NOTHING_CHANGED, Problem } from "@/components/ApiProblem";
import { ConnectTikTok } from "@/components/ConnectTikTok";
import { DisconnectAction } from "@/components/SettingsForms";

export const metadata = { title: "Disconnect this shop" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function DisconnectPage({ params }) {
  const { shopId } = await params;
  const result = await api("/shops", { cache: "no-store" });
  const problem = apiProblem(result, { what: "this shop", note: NOTHING_CHANGED });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["Shop"][]} */
  const shops = result.data?.shops ?? [];
  const shop = shops.find((s) => s.id === shopId);
  if (!shop) {
    return <Problem title="That shop is not on your account." note="Check the address and try again." />;
  }

  const plan = (
    <>Disconnecting does not change your plan, and you can stop it renewing in <Link href={`/shops/${shopId}/settings/profile`}>Profile and plan</Link>.</>
  );

  if (shop.connection_status === "disconnected") {
    return (
      <section data-testid="disconnect-screen">
        <header className="page-head">
          <h1>This shop is already disconnected</h1>
          <p>MyShopEdge is not reading {shop.shop_name ?? "this shop"} from TikTok, so there is nothing to disconnect. {plan}</p>
        </header>
        <div className="stack">
          <div className="card" data-testid="disconnect-already">
            <h2>Connect it again</h2>
            <p className="card__why">Approve MyShopEdge again on TikTok&rsquo;s own page. MyShopEdge then reads from where it stopped and adds what you missed to the records you already have.</p>
            <ConnectTikTok />
          </div>
          <p><Link href={`/shops/${shopId}/settings`}>Back to settings</Link></p>
        </div>
      </section>
    );
  }

  return (
    <section data-testid="disconnect-screen">
      <header className="page-head">
        <h1>Disconnect this shop</h1>
        <p>MyShopEdge stops reading from TikTok. Nothing you already have is deleted. {plan}</p>
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
