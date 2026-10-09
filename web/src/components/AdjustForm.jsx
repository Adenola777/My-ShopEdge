"use client";

/**
 * S25, a manual stock adjustment. The count moves in MyShopEdge only. PRD 6.2 excludes
 * writing stock back to TikTok, and the screen says so before saving, because a seller
 * would otherwise expect TikTok's count to change too.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { newKey } from "@/lib/money-input";

/** @param {{ shopId: string, skuId: string }} props */
export function AdjustForm({ shopId, skuId }) {
  const router = useRouter();
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(/** @type {string | null} */ (null));

  /** @param {React.FormEvent} e */
  async function save(e) {
    e.preventDefault();
    if (!/^[+-]?\d+$/.test(quantity.trim()) || Number(quantity) === 0) {
      setError("Enter a whole number of units, negative to remove them, for example -2.");
      return;
    }
    if (reason.trim() === "") {
      setError("Say why, so the change can be traced later.");
      return;
    }
    setBusy(true);
    setError(null);
    setSaved(null);
    const r = await api(`/shops/${encodeURIComponent(shopId)}/stock/${encodeURIComponent(skuId)}/adjustments`, {
      method: "POST",
      body: JSON.stringify({ quantity: Number(quantity), reason: reason.trim() }),
      idempotencyKey: newKey(),
    });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable ? "MyShopEdge could not be reached, so nothing was changed." : (r.data?.detail ?? "The adjustment was not saved."));
      return;
    }
    const n = Math.abs(Number(quantity));
    const units = `${n} ${n === 1 ? "unit" : "units"}`;
    setSaved(
      Number(quantity) > 0
        ? `The adjustment is saved. MyShopEdge added ${units} to your count.`
        : `The adjustment is saved. MyShopEdge took ${units} off your count.`,
    );
    setQuantity("");
    setReason("");
    router.refresh();
  }

  return (
    <form onSubmit={save} className="card stack">
      <h2>Adjust the count</h2>
      <p className="rows__sub">
        This changes your count in MyShopEdge only, and TikTok&rsquo;s own figure stays as it
        is. If you add units here and TikTok&rsquo;s count later rises by no more than your
        alert setting allows, MyShopEdge takes those units off your adjustment so they are not
        counted twice. A larger rise is flagged in Discrepancies for you to check.
      </p>
      <div>
        <label htmlFor="adj-qty">Units to add, or a minus number to remove</label>
        <input id="adj-qty" inputMode="numeric" placeholder="-2" value={quantity}
               onChange={(e) => setQuantity(e.target.value)} />
      </div>
      <div>
        <label htmlFor="adj-reason">Reason</label>
        <input id="adj-reason" maxLength={500} placeholder="Two damaged in the stockroom"
               value={reason} onChange={(e) => setReason(e.target.value)} />
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {saved && !error && <p className="rows__sub" role="status">{saved}</p>}
      <p><button className="btn btn--primary" disabled={busy}>{busy ? "Saving" : "Save adjustment"}</button></p>
    </form>
  );
}
