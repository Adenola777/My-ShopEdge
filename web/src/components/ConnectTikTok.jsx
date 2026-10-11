"use client";

/**
 * The action on S1 Connect TikTok Shop. `authorizeTiktok` returns a link with a single use
 * state bound to this seller, valid for ten minutes, and the browser goes there.
 *
 * `return_to` is `/shops`, which the service accepts because it is a path with one leading
 * slash (`_safe_return_to` in connections.py).
 */

import { useState } from "react";
import { api } from "@/lib/api";

/** Wording for the refusals `authorize_tiktok` can give. Anything else shows its detail. */
const REFUSAL = {
  tiktok_unconfigured:
    "We could not connect your shop just now. Nothing has changed, and you can try again in a few minutes.",
  unauthenticated: "Your session has ended. Sign in again, then connect your shop.",
};

export function ConnectTikTok() {
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [busy, setBusy] = useState(false);
  // A38: the plan's shop limit, when the service refused a new shop for it.
  const [limit, setLimit] = useState(/** @type {number | null} */ (null));

  async function connect() {
    setBusy(true);
    setError(null);
    const r = await api("/connections/tiktok/authorize", {
      method: "POST",
      body: JSON.stringify({ return_to: "/shops" }),
    });
    if (r.ok && r.data?.authorization_url) {
      window.location.assign(r.data.authorization_url);
      return;
    }
    setBusy(false);
    if (r.unreachable) {
      setError("MyShopEdge could not be reached. Try again in a moment.");
      return;
    }
    if (r.data?.code === "shop_limit_reached") {
      setLimit(Number(r.data?.shop_limit ?? 1));
      return;
    }
    const code = /** @type {keyof typeof REFUSAL} */ (r.data?.code);
    setError(REFUSAL[code] ?? r.data?.detail ?? "The connection could not be started. Nothing has changed. Try again in a moment.");
  }

  if (limit !== null) {
    return (
      <div className="note note--warn" role="status" data-testid="shop-limit">
        <h2>You have reached your shop limit</h2>
        <p>
          Your current plan includes {limit === 1 ? "1 TikTok Shop" : `${limit} TikTok Shops`}.
          Upgrade to connect more shops and manage them in one place.
        </p>
        <p className="upload__actions">
          <a className="btn btn--primary btn--small" href="/pricing">Upgrade</a>
          <a className="btn btn--quiet btn--small" href="/shops">Manage shops</a>
        </p>
      </div>
    );
  }

  return (
    <div className="stack">
      {error && <p className="form-error" role="alert">{error}</p>}
      <p>
        <button className="btn btn--primary btn--block" type="button" onClick={connect} disabled={busy}>
          {busy ? "Opening TikTok Shop" : "Connect with TikTok Shop"}
        </button>
      </p>
      <p className="footnote">You approve access on TikTok&rsquo;s own page, then come back here.</p>
    </div>
  );
}
