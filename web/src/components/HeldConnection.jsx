"use client";

/**
 * What the callback page shows when `tiktokCallback` answered 202: TikTok's approval arrived
 * without a state MyShopEdge issued, and it is held until the seller signs in and confirms the
 * shop (migration 0037, 25 October 2026). See PendingTikTokClaim for why.
 *
 * The claim is written to this tab's session storage straight away, so a seller who signs in
 * or creates an account is asked to confirm the shop on the first shop screen they reach.
 */

import { useEffect } from "react";
import { PendingTikTokClaim, keepHeld, shopNames } from "./PendingTikTokClaim";

/** @param {{ held: import("./PendingTikTokClaim").HeldConnection, signedIn: boolean }} props */
export function HeldConnection({ held, signedIn }) {
  useEffect(() => {
    keepHeld(held);
  }, [held]);

  if (signedIn) return <PendingTikTokClaim held={held} />;

  const names = shopNames(held.shops);
  return (
    <section className="state" data-testid="held-connection">
      <h1>Sign in to finish connecting {names}.</h1>
      <p>
        TikTok Shop approved MyShopEdge to read {names}. Sign in, or create an account, in this
        tab within thirty minutes, and you will be asked to confirm the shop.
      </p>
      <p className="upload__actions">
        <a className="btn btn--primary" href="/handler/sign-in">Sign in</a>
        <a className="btn btn--quiet" href="/handler/sign-up">Create an account</a>
      </p>
    </section>
  );
}
