"use client";

/** The one button that changes the plan, through updateSubscription. */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

/** @param {{ plan: string, name: string, back: string }} props */
export function ChangePlanForm({ plan, name, back }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  async function change() {
    setBusy(true);
    setError(null);
    const r = await api("/billing/subscription", { method: "PATCH", body: JSON.stringify({ plan }) });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable
        ? "MyShopEdge could not be reached, so your plan was not changed."
        : (r.data?.detail ?? "Your plan was not changed. Please try again."));
      return;
    }
    router.push(back);
    router.refresh();
  }

  return (
    <>
      <p>
        <button type="button" className="btn btn--primary btn--block" disabled={busy} onClick={change}
          data-testid="change-plan-submit">
          {busy ? "One moment" : `Move to ${name}`}
        </button>
      </p>
      {error ? <p className="form-error" role="alert">{error}</p> : null}
    </>
  );
}
