"use client";

/**
 * S21, add or change one variant's cost price. The service keeps the old cost and stamps it
 * superseded (CST-4), so saving here never overwrites a cost.
 *
 * The date says which sales the cost applies to (effective_from, which putSkuCost has always
 * accepted). Each unit is costed at the cost in force on its sale date (A31.4), so until
 * 8 October 2026, when this form sent no date, a cost applied from the day it was saved and
 * a variant that sold before then stayed without a cost for those sales. A cost already set
 * from a later date keeps applying from that later date: checked on the local copy the same
 * day, a cost dated 1 August costed 15 August and left 8 October on the cost dated then.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { newKey, parsePounds } from "@/lib/money-input";

/** @param {{ shopId: string, skuId: string, currency?: string, variantName?: string }} props */
export function CostForm({ shopId, skuId, currency = "GBP", variantName }) {
  const router = useRouter();
  const today = londonToday();
  const [value, setValue] = useState("");
  const [from, setFrom] = useState(today);
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [busy, setBusy] = useState(false);

  /** @param {React.FormEvent} e */
  async function save(e) {
    e.preventDefault();
    const pence = parsePounds(value);
    if (pence === null) {
      setError("Enter the cost in pounds and pence, for example 3.40.");
      return;
    }
    if (!from || from > today) {
      setError("Choose a date on or before today for the sales this cost applies to.");
      return;
    }
    setBusy(true);
    setError(null);
    const r = await api(`/shops/${encodeURIComponent(shopId)}/skus/${encodeURIComponent(skuId)}/cost`, {
      method: "PUT",
      body: JSON.stringify({ cost: { amount_minor: pence, currency }, effective_from: from }),
      idempotencyKey: newKey(),
    });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable ? "MyShopEdge could not be reached, so nothing was saved." : (r.data?.detail ?? "The cost was not saved."));
      return;
    }
    setValue("");
    setFrom(today);
    router.refresh();
  }

  return (
    <form onSubmit={save} className="inline-form">
      <label className="visually-hidden" htmlFor={`cost-${skuId}`}>
        {variantName ? `Cost price per unit for ${variantName}` : "Cost price per unit"}
      </label>
      <input
        id={`cost-${skuId}`}
        inputMode="decimal"
        placeholder="0.00"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        aria-describedby={error ? `cost-${skuId}-error` : undefined}
      />
      <label htmlFor={`cost-from-${skuId}`}>For units sold from</label>
      <input
        id={`cost-from-${skuId}`}
        type="date"
        max={today}
        value={from}
        onChange={(e) => setFrom(e.target.value)}
      />
      <button className="btn btn--quiet" disabled={busy || value.trim() === ""}>
        {busy ? "Saving" : "Save cost"}
      </button>
      {error && <p id={`cost-${skuId}-error`} className="form-error" role="alert">{error}</p>}
    </form>
  );
}

/** Today's date in London, as YYYY-MM-DD, the way the service dates a sale (A29.9). */
function londonToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/London" }).format(new Date());
}
