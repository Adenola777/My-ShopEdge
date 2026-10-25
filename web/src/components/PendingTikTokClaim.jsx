"use client";

/**
 * Finishes a TikTok approval that arrived without a state MyShopEdge issued (migration 0037,
 * 25 October 2026).
 *
 * The callback page receives a one-time claim from `tiktokCallback` when TikTok sent the seller
 * back with no state of ours, which is what happens when a seller installs the app from
 * TikTok's App & Service Store. The claim is kept in this tab's session storage so that it
 * survives the seller signing in or creating an account. Once signed in, the seller is shown
 * the shop's name and must confirm it before `claimTikTokConnection` attaches it. That
 * confirmation stands in for the state: without it, somebody could send a seller a link that
 * carries their own approval and attach their shop to the seller's account.
 *
 * Session storage belongs to one tab and one address, and it is cleared when the tab closes.
 * A seller who signs in in another tab therefore has to connect again, which is the safe way
 * round. The claim itself lasts thirty minutes on the service.
 *
 * **Unverified against TikTok.** No approval without our state has yet reached the service.
 */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export const CLAIM_KEY = "mse.tiktokClaim";

/**
 * @typedef {Object} HeldConnection
 * @property {string} claim
 * @property {string} expires_at
 * @property {{ tiktok_shop_id: string, tiktok_shop_code?: string | null, shop_name?: string | null, region?: string | null }[]} shops
 */

/** Wording for what `claimTikTokConnection` can refuse. Anything else shows its detail. */
const REFUSAL = {
  claim_invalid: "That connection has expired or was already finished. Connect your shop again.",
  shop_already_connected:
    "That shop is already connected to another MyShopEdge account. Sign in with the account that connected it.",
  shop_limit_reached:
    "Your current plan has no room for another TikTok Shop, so nothing was connected. Upgrade on Plans and pricing, then connect your shop again.",
  unauthenticated: "Your session has ended. Sign in again, then connect your shop again.",
};

/** @returns {HeldConnection | null} */
export function readHeld() {
  try {
    const held = JSON.parse(window.sessionStorage.getItem(CLAIM_KEY) ?? "null");
    if (!held?.claim || !Array.isArray(held.shops)) return null;
    if (Date.parse(held.expires_at) <= Date.now()) {
      window.sessionStorage.removeItem(CLAIM_KEY);
      return null;
    }
    return held;
  } catch {
    return null;
  }
}

/** @param {HeldConnection} held */
export function keepHeld(held) {
  try {
    window.sessionStorage.setItem(CLAIM_KEY, JSON.stringify(held));
  } catch {
    // Storage can be refused in a private window. The page that holds the claim still offers
    // the confirmation while it is open, so nothing more is needed here.
  }
}

function forget() {
  try {
    window.sessionStorage.removeItem(CLAIM_KEY);
  } catch {
    // Nothing to clear.
  }
}

/** @param {HeldConnection["shops"]} shops */
export function shopNames(shops) {
  const names = shops.map((s) => s.shop_name || s.tiktok_shop_code || "your TikTok Shop");
  return names.length <= 1 ? names[0] ?? "your TikTok Shop" : `${names.slice(0, -1).join(", ")} and ${names.at(-1)}`;
}

/**
 * The confirmation. Given `held`, it uses that; otherwise it reads session storage, so it can
 * sit on every shop screen and appear only when a claim is waiting.
 *
 * @param {{ held?: HeldConnection | null }} props
 */
export function PendingTikTokClaim({ held: given = null }) {
  const [held, setHeld] = useState(/** @type {HeldConnection | null} */ (given));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  useEffect(() => {
    if (!given) setHeld(readHeld());
  }, [given]);

  if (!held && !error) return null;

  async function connect() {
    if (!held) return;
    setBusy(true);
    setError(null);
    const r = await api("/connections/tiktok/claim", {
      method: "POST",
      body: JSON.stringify({ claim: held.claim }),
      timeoutMs: 45000,
    });
    if (r.unreachable) {
      // The claim may or may not have been spent, so it is kept and the seller may try again.
      setBusy(false);
      setError("MyShopEdge could not be reached. Try again in a moment.");
      return;
    }
    forget();
    if (r.ok) {
      const shop = r.data?.shop;
      window.location.assign(shop?.id && r.data?.accepted ? `/shops/${shop.id}/sync?connected=1` : "/shops?all=1");
      return;
    }
    setBusy(false);
    setHeld(null);
    const code = /** @type {keyof typeof REFUSAL} */ (r.data?.code);
    setError(REFUSAL[code] ?? r.data?.detail ?? "The shop could not be connected. Connect your shop again.");
  }

  function decline() {
    forget();
    setHeld(null);
  }

  if (!held) {
    return (
      <aside className="content">
        <div className="note note--warn" role="alert" data-testid="claim-refused">
          <p>{error}</p>
        </div>
      </aside>
    );
  }

  const names = shopNames(held.shops);
  return (
    <aside className="content" aria-labelledby="pending-claim-title">
      <div className="note note--info" data-testid="pending-claim">
        <h2 id="pending-claim-title">Finish connecting {names}</h2>
        <p>
          TikTok Shop approved MyShopEdge to read {names}. Connect it to the account you are signed
          in with only if it is your shop.
        </p>
        {error && <p className="form-error" role="alert">{error}</p>}
        <p className="upload__actions">
          <button className="btn btn--primary btn--small" type="button" onClick={connect} disabled={busy}>
            {busy ? "Connecting" : `Connect ${names}`}
          </button>
          <button className="btn btn--quiet btn--small" type="button" onClick={decline} disabled={busy}>
            This is not my shop
          </button>
        </p>
      </div>
    </aside>
  );
}
