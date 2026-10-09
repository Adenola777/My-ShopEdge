"use client";

/**
 * The two actions of A30.1: asking for the account to be deleted (S30), and cancelling that
 * request during its thirty days. Written 28 September 2026.
 *
 * What the seller is told comes from the service's answer, `includes`, rather than from
 * this file, so the record the seller keeps is the one the service acted on.
 */

import { useState } from "react";
import { api, formatDate } from "@/lib/api";
import { newKey } from "@/lib/money-input";

/** @typedef {import("@/lib/api-types").components["schemas"]["DeletionAcknowledgement"]} Ack */

export function DeleteAccountForm() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [ack, setAck] = useState(/** @type {Ack | null} */ (null));
  const [key] = useState(() => newKey());

  /** @param {import("react").FormEvent} e */
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const r = await api("/me", {
      method: "DELETE",
      idempotencyKey: key,
      body: JSON.stringify({ confirm_email: email.trim() }),
    });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable ? "MyShopEdge could not be reached, so nothing was deleted." : (r.data?.detail ?? "Your account was not closed. Please try again in a moment."));
      return;
    }
    setAck(/** @type {Ack} */ (r.data));
  }

  if (ack) {
    return (
      <div className="stack" data-testid="deletion-accepted">
        <div className="card">
          <h2>Your account is closing</h2>
          <p className="card__why">MyShopEdge does not email this record, so please save or print this page before you sign out.</p>
          <ul className="stack">
            {ack.includes.map((line) => <li key={line}>{line}</li>)}
          </ul>
          {ack.invoices_retained_until && (
            <p className="note">MyShopEdge keeps your TikTok fee invoices until at least {formatDate(ack.invoices_retained_until)}, because VAT records must be kept for six years.</p>
          )}
        </div>
        <p><a className="btn btn--primary btn--block" href="/handler/sign-out">Sign out</a></p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="stack" data-testid="delete-form">
      <div>
        <label htmlFor="confirm-email">Type the email address on this account</label>
        <input id="confirm-email" type="email" autoComplete="off" value={email}
               onChange={(e) => setEmail(e.target.value)} data-testid="confirm-email" />
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <p>
        <button className="btn btn--quiet btn--block" disabled={busy || email.trim() === ""} data-testid="confirm-delete">
          {busy ? "Deleting your account" : "Delete my account"}
        </button>
      </p>
    </form>
  );
}

/**
 * The cancel button, with the closing page's explanation passed in as `children`. Since
 * 9 October 2026 a cancellation that succeeds replaces both with a confirmation, because
 * until then the seller was sent to /shops with nothing to say the account was kept. The
 * confirmation reads `shops_disconnected` from cancelAccountDeletion's answer, and says each
 * shop must be connected again because `cancel_account_deletion` in account_deletion.py
 * leaves every shop disconnected.
 *
 * @param {{ children?: import("react").ReactNode }} props
 */
export function CancelDeletion({ children }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [kept, setKept] = useState(/** @type {{ shops_disconnected: number } | null} */ (null));

  async function cancel() {
    setBusy(true);
    setError(null);
    const r = await api("/me/deletion/cancel", { method: "POST" });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable ? "MyShopEdge could not be reached, so the deletion still stands." : (r.data?.detail ?? "The deletion was not cancelled."));
      return;
    }
    setKept({ shops_disconnected: Number(r.data?.shops_disconnected ?? 0) });
  }

  if (kept) {
    const n = kept.shops_disconnected;
    return (
      <div className="stack" data-testid="deletion-cancelled">
        <h1>Your account is active again</h1>
        <p role="status">The deletion is cancelled, and nothing will be erased.</p>
        {n > 0 && (
          <p>
            {n === 1 ? "Your shop is" : `Your ${n} shops are`} still disconnected, because closing the
            account stopped MyShopEdge using your TikTok sign-in details. Connect {n === 1 ? "it" : "each one"} again
            on TikTok so MyShopEdge can read new orders and payments. Your records are all still here.
          </p>
        )}
        <p><a className="btn btn--primary btn--block" href="/shops" data-testid="deletion-cancelled-shops">Go to your shops</a></p>
      </div>
    );
  }

  return (
    <div className="stack">
      {children}
      {error && <p className="form-error" role="alert">{error}</p>}
      <p>
        <button className="btn btn--primary btn--block" onClick={cancel} disabled={busy} data-testid="cancel-deletion">
          {busy ? "Cancelling" : "Keep my account"}
        </button>
      </p>
    </div>
  );
}
