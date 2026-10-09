/**
 * S28 Connection problem. It reads the shop's `connection_status` from listShops and tells
 * the seller plainly what the state means for their figures and how to put it right. A
 * connected shop is sent to Today, so the screen is never a dead end.
 *
 * Emergent AI wrote the first version in `Adenola777/MYSHOPEDGE` (commit 3f1bd43). It was
 * corrected on 28 September 2026: it handled `error` and `expired`, which the contract's
 * `connection_status` never holds, and it missed `needs_reconnect`, the state a lapsed
 * authorisation actually produces. The states below are the contract's four.
 *
 * Reconnecting uses the same button as S1. The callback upserts the shop on its TikTok id,
 * so the same shop comes back to the same records.
 */

import Link from "next/link";
import { redirect } from "next/navigation";
import { api, formatDate } from "@/lib/api";
import { apiProblem, NOTHING_CHANGED } from "@/components/ApiProblem";
import { ConnectTikTok } from "@/components/ConnectTikTok";

export const metadata = { title: "Connection problem" };

/** @typedef {{ head: string, body: string, reconnect: boolean }} State */

/** @type {State} */
const DISCONNECTED = {
  head: "Your TikTok Shop is disconnected",
  body: "MyShopEdge has stopped reading from TikTok, so your figures will not update. Your records are still here. Reconnect the same shop at any time and everything continues from where it stopped. Your plan is not changed while the shop is disconnected.",
  reconnect: true,
};

/** @type {Record<string, State>} */
const STATE = {
  needs_reconnect: {
    head: "Your TikTok Shop needs reconnecting",
    body: "MyShopEdge needs your approval on TikTok again. Until you give it, new orders, returns and payments are not read, and your figures stop at the last successful read.",
    reconnect: true,
  },
  disconnected: DISCONNECTED,
  pending: {
    head: "Your shop is still being read",
    body: "The connection is made and the first read from TikTok has not finished. Figures appear as each part arrives.",
    reconnect: false,
  },
};

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function ConnectionProblemPage({ params }) {
  const { shopId } = await params;
  const result = await api("/shops", { cache: "no-store" });
  const problem = apiProblem(result, { what: "this shop", note: NOTHING_CHANGED });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["Shop"][]} */
  const shops = result.data?.shops ?? [];
  const shop = shops.find((s) => s.id === shopId);
  if (!shop) redirect("/shops");
  if (shop.connection_status === "connected") redirect(`/shops/${shopId}/today`);

  const state = STATE[shop.connection_status] ?? DISCONNECTED;

  return (
    <section data-testid="connection-problem-screen">
      <header className="page-head">
        <h1>{state.head}</h1>
        <p>{shop.shop_name ?? "Your shop"}</p>
      </header>
      <div className="stack">
        <div className="note note--warn" role="status" data-testid="connection-status">
          <p>{state.body}</p>
          <p data-testid="connection-last-read">
            {shop.last_synced_at
              ? `MyShopEdge last finished a read of this shop on ${formatDate(shop.last_synced_at, { time: true })}.`
              : "MyShopEdge has not yet finished a read of this shop."}
          </p>
        </div>
        {state.reconnect ? (
          <div className="card">
            <h2>Reconnect your shop</h2>
            <p className="card__why">Approve MyShopEdge again on TikTok&rsquo;s own page.</p>
            <ConnectTikTok />
          </div>
        ) : (
          <p>
            <Link className="btn btn--primary btn--block" href={`/shops/${shopId}/sync`}>
              See what has been read so far
            </Link>
          </p>
        )}
      </div>
    </section>
  );
}
