/**
 * Where TikTok sends a seller back after they approve MyShopEdge.
 *
 * TikTok redirects the browser here with `code` and `state`. This page, on the server, hands
 * both to the service's `tiktokCallback`, which spends the state, exchanges the code, stores
 * the encrypted tokens and creates the shop, then tells the seller what happened in words.
 *
 * Why the redirect lands here and not on the service. The service answers `tiktokCallback`
 * with JSON, as the contract says, so a browser sent straight to it shows the seller a page
 * of raw data. Landing here keeps the contract as it is and gives the seller a screen. The
 * callback URL registered in TikTok Partner Center must therefore be this path on the app's
 * address: `https://app.myshopedge.inspirecraftglobal.com/connections/tiktok/callback` since
 * 30 September 2026, when the owner set it, and the `vercel.app` address before that. The
 * path is the one the runbook named on 23 September before any code existed.
 *
 * The page is not behind sign-in, because `tiktokCallback` carries `security: []`: the
 * state is what binds the result to the seller who started it.
 *
 * **Unverified against TikTok.** No real authorisation has passed through this page. What
 * TikTok puts in the address when a seller declines is not recorded in A23, so an arrival
 * without a `code` is treated as a connection that did not complete.
 *
 * **25 October 2026.** An arrival with a `code` and no `state`, or a state the service did not
 * issue, is no longer refused. A seller who installs the app from TikTok's App & Service Store
 * starts on TikTok's side, and whether TikTok then sends any state is unverified. The service
 * answers 202 with a one-time claim, and `HeldConnection` asks the seller to sign in and
 * confirm the shop by name before it is attached (migration 0037).
 */

import Link from "next/link";
import { redirect } from "next/navigation";
import { api } from "@/lib/api";
import { Problem } from "@/components/ApiProblem";
import { HeldConnection } from "@/components/HeldConnection";
import { STACK_CONFIGURED, currentUser } from "@/lib/stack";

export const metadata = { title: "Your shop connection" };
export const dynamic = "force-dynamic";

/** What each refusal from `tiktok_callback` means to a seller. */
const REFUSAL = {
  state_invalid: [
    "That connection link has expired.",
    "A connection link lasts ten minutes and works once. Start the connection again.",
  ],
  not_a_seller_account: [
    "That TikTok account is not a Shop seller account.",
    "Sign in to TikTok with the account that owns your shop, then start again.",
  ],
  no_authorised_shop: [
    "No shop was shared with MyShopEdge.",
    "TikTok did not return a shop for that account. Start again and approve your shop.",
  ],
  shop_already_connected: [
    "That shop is already connected to another MyShopEdge account.",
    "Each shop can belong to one account. Sign in with the account that connected it.",
  ],
  shop_limit_reached: [
    "You have reached your shop limit.",
    "Your current plan has no room for another TikTok Shop, so nothing was connected. Upgrade on Plans and pricing to connect more shops.",
  ],
  tiktok_unconfigured: [
    "We could not connect your shop just now.",
    "Nothing has changed, and you can try again in a few minutes.",
  ],
  token_encryption_unconfigured: [
    "We could not connect your shop just now.",
    "Nothing has changed, and you can try again in a few minutes.",
  ],
};

/** Why a connected shop cannot produce figures, from `rejection_reason`. */
const NOT_SUPPORTED = {
  region_unsupported: "MyShopEdge reads UK shops only, and this shop is registered elsewhere.",
  seller_type_unsupported:
    "MyShopEdge reads shops that sell locally in the UK, and this shop sells cross border.",
};

/**
 * Where "start again" leads. `/shops` sends a seller who already has a shop straight into it,
 * so that seller is sent to the page that connects another one. When the shops cannot be read,
 * `/shops` is the safe default.
 *
 * @returns {Promise<{ href: string, label: string }>}
 */
async function startAgainLink() {
  const shops = await api("/shops", { cache: "no-store" });
  const has = shops.ok && (shops.data?.shops ?? []).length > 0;
  return has ? { href: "/shops/connect", label: "Connect again" } : { href: "/shops", label: "Start again" };
}

/** @param {{ searchParams: Promise<Record<string, string>> }} props */
export default async function TikTokCallbackPage({ searchParams }) {
  const { code, state } = await searchParams;

  if (!code) {
    return (
      <Problem
        title="The connection was not completed."
        note="TikTok sent you back without approving access, so nothing was connected. You can start again whenever you like."
        startAgain={await startAgainLink()}
      />
    );
  }

  const qs = new URLSearchParams(state ? { code, state } : { code }).toString();
  const result = await api(`/connections/tiktok/callback?${qs}`, {
    cache: "no-store",
    timeoutMs: 45000,
  });

  if (result.unreachable) {
    return (
      <Problem
        title="MyShopEdge could not be reached."
        note="Your approval may not have been saved. Start the connection again in a moment."
        startAgain
      />
    );
  }

  if (!result.ok) {
    const code = /** @type {keyof typeof REFUSAL} */ (result.data?.code);
    const [title, note] = /** @type {[string, string]} */ (REFUSAL[code] ?? [
      "The shop could not be connected.",
      "Nothing has changed. Start again in a few minutes.",
    ]);
    return <Problem title={title} note={note} startAgain={await startAgainLink()} />;
  }

  if (result.status === 202) {
    const signedIn = !STACK_CONFIGURED || Boolean(await currentUser());
    return <HeldConnection held={result.data} signedIn={signedIn} />;
  }

  /** @type {{ shop: any, accepted: boolean, rejection_reason: string | null }} */
  const { shop, accepted, rejection_reason } = result.data;
  const name = shop?.shop_name ?? shop?.tiktok_shop_id ?? "Your shop";

  if (!accepted) {
    const reason = /** @type {keyof typeof NOT_SUPPORTED} */ (rejection_reason);
    return (
      <section className="state">
        <h1>{name} is connected, but MyShopEdge cannot read it.</h1>
        <p>{NOT_SUPPORTED[reason] ?? "MyShopEdge does not read this kind of shop."}</p>
        <p>MyShopEdge does not read this shop, so no figures will appear for it.</p>
        <p>
          <Link className="btn btn--primary" href="/shops">
            Back to your shops
          </Link>
        </p>
      </section>
    );
  }

  // A36 step 2 (the brief's section 4): a connected shop goes straight on to its import, with
  // no extra click. The import page says the shop is connected.
  if (shop?.id) redirect(`/shops/${shop.id}/sync?connected=1`);

  return (
    <section className="state">
      <h1>{name} is connected.</h1>
      <p>
        MyShopEdge only reads your shop and never changes it. We are reading your orders,
        returns and payouts now, and your figures fill in as they arrive.
      </p>
      <p>
        {/* A14.2: the step after connecting is S2 First sync, not Today. */}
        <Link className="btn btn--primary" href={shop?.id ? `/shops/${shop.id}/sync` : "/shops"}>
          See your shop being read
        </Link>
      </p>
    </section>
  );
}
