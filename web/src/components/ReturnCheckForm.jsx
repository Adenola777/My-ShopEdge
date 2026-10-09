"use client";

/**
 * The form on S8 Return check, drawn to wireframe sheet 05: the seller says whether the
 * item came back usable, enters any return shipping they paid, sees what the check will do,
 * and records it. Checking is one way, so no choice is made for the seller in advance.
 *
 * What each choice writes is the service's rule (checkReturnItem, A30.2), and the "What this check records"
 * card describes it without working out any money here: a write-off is valued by the service
 * at the cost in force when the unit sold, so the card names the rule rather than a figure.
 */

import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { api, formatMoney } from "@/lib/api";
import { newKey, parsePounds } from "@/lib/money-input";

/** @typedef {"resellable" | "unsellable" | "not_applicable"} CheckStatus */

/** @param {{ shopId: string, itemId: string, quantity: number, currency: string }} props */
export function ReturnCheckForm({ shopId, itemId, quantity, currency }) {
  const router = useRouter();
  const pathname = usePathname();
  const [status, setStatus] = useState(/** @type {CheckStatus | null} */ (null));
  const [postage, setPostage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [key] = useState(() => newKey());

  const units = `${quantity} ${quantity === 1 ? "unit" : "units"}`;
  const shownPostage = postage.trim() === "" ? null : parsePounds(postage);

  /** @param {import("react").FormEvent} e */
  async function confirm(e) {
    e.preventDefault();
    if (status === null) {
      setError("Say how the item came back before you record the check.");
      return;
    }
    let postageMinor = null;
    if (status !== "not_applicable" && postage.trim() !== "") {
      postageMinor = parsePounds(postage);
      if (postageMinor === null) {
        setError("Enter the return shipping in pounds, for example 2.85.");
        return;
      }
    }
    setBusy(true);
    setError(null);
    const r = await api(`/shops/${encodeURIComponent(shopId)}/return-items/${encodeURIComponent(itemId)}/check`, {
      method: "POST",
      idempotencyKey: key,
      body: JSON.stringify({
        seller_check_status: status,
        ...(postageMinor !== null ? { return_postage: { amount_minor: postageMinor, currency } } : {}),
      }),
    });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable ? "MyShopEdge could not be reached, so nothing was recorded." : (r.data?.detail ?? "The check was not recorded."));
      return;
    }
    // The checked item leaves the list, and this form with it, so the page says what was
    // recorded from the address (copy audit finding 121).
    router.replace(`${pathname}?${new URLSearchParams({ checked: status })}`, { scroll: false });
    router.refresh();
  }

  return (
    <form onSubmit={confirm} className="stack" data-testid={`check-form-${itemId}`}>
      <p id={`how-${itemId}`} style={{ margin: 0 }}><strong>How did it come back?</strong></p>
      <fieldset className="segmented" aria-labelledby={`how-${itemId}`}>
        {/** @type {[CheckStatus, string][]} */ ([
          ["resellable", "Resellable"],
          ["unsellable", "Unsellable"],
          ["not_applicable", "Nothing came back"],
        ]).map(([value, label]) => (
          <label key={value} className={status === value ? "segmented__on" : undefined}>
            <input type="radio" name={`status-${itemId}`} value={value} checked={status === value}
                   onChange={() => setStatus(value)} />
            {label}
          </label>
        ))}
      </fieldset>

      {status !== null && status !== "not_applicable" && (
        <div>
          <label htmlFor={`postage-${itemId}`}>Return shipping you paid (£)</label>
          <input id={`postage-${itemId}`} inputMode="decimal" placeholder="0.00" value={postage}
                 onChange={(e) => setPostage(e.target.value)} data-testid="return-postage" />
        </div>
      )}

      {status !== null && (
        <div className="card">
          <h3>What this check records</h3>
          <ul className="rows">
            {status === "resellable" && <li><span>Stock</span><strong>+{units}</strong></li>}
            {status === "unsellable" && (
              <li>
                <span>Write off</span>
                <strong>{units} at the cost in force when {quantity === 1 ? "it" : "they"} sold</strong>
              </li>
            )}
            {status === "not_applicable" && <li><span>Stock</span><strong>No change</strong></li>}
            {status !== "not_applicable" && shownPostage !== null && (
              <li><span>Return shipping you paid</span><strong>{formatMoney({ amount_minor: shownPostage, currency })}</strong></li>
            )}
          </ul>
        </div>
      )}

      {error && <p className="form-error" role="alert">{error}</p>}
      <p>
        <button className="btn btn--primary btn--block" disabled={busy} data-testid="confirm-return">
          {busy ? "Recording" : "Record this check"}
        </button>
      </p>
      <p className="footnote">A check is recorded once and cannot be changed.</p>
    </form>
  );
}
