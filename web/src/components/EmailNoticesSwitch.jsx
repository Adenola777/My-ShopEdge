"use client";

/**
 * The seller's switch for notice emails, on S41 Profile and plan. Added 10 October 2026 with
 * migration 0031, for NTF-2's "unless they opt out". It changes `email_notices` through
 * updateMe. Before 0031 is applied the service answers 503 and the switch says nothing changed.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

/** @param {{ on: boolean }} props */
export function EmailNoticesSwitch({ on }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  async function change() {
    setBusy(true);
    setError(null);
    const r = await api("/me", {
      method: "PATCH",
      body: JSON.stringify({ email_notices: !on }),
    });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable
        ? "MyShopEdge could not be reached, so nothing was changed."
        : (r.data?.detail ?? "Nothing was changed. Please try again."));
      return;
    }
    router.refresh();
  }

  return (
    <div className="card" data-testid="profile-email">
      <h2>Email notices</h2>
      <p>
        {on
          ? "MyShopEdge emails you when your shop's connection stops working, when you pass your plan's orders, and when a scheduled export is ready."
          : "MyShopEdge does not email you. Every notice still appears in Notifications."}
      </p>
      <p>
        <button type="button" className="btn btn--quiet btn--block" disabled={busy}
          onClick={change} data-testid="profile-email-switch">
          {busy ? "One moment" : on ? "Stop email notices" : "Send me email notices"}
        </button>
      </p>
      {error ? <p className="form-error" role="alert">{error}</p> : null}
    </div>
  );
}
