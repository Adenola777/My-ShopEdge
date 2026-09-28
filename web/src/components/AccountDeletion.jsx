"use client";

/**
 * The two actions of A30.1: asking for the account to be deleted (S30), and cancelling that
 * request during its thirty days. Written 28 September 2026.
 *
 * What the seller is told comes from the service's answer, `includes`, rather than from
 * this file, so the record the seller keeps is the one the service acted on.
 */

import { useRouter } from "next/navigation";
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
      setError(r.unreachable ? "MyShopEdge could not be reached, so nothing was deleted." : (r.data?.detail ?? "The account was not deleted."));
      return;
    }
    setAck(/** @type {Ack} */ (r.data));
  }

  if (ack) {
    return (
      <div className="stack" data-testid="deletion-accepted">
        <div className="card">
          <h2>Your account is closing</h2>
          <p className="card__why">Keep this as your record of what you asked for.</p>
          <ul className="stack">
            {ack.includes.map((line) => <li key={line}>{line}</li>)}
          </ul>
          {ack.invoices_retained_until && (
            <p className="note">Your TikTok fee invoices are kept until {formatDate(ack.invoices_retained_until)}, because VAT records must be.</p>
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
          {busy ? "Deleting" : "Delete my account"}
        </button>
      </p>
    </form>
  );
}

export function CancelDeletion() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  async function cancel() {
    setBusy(true);
    setError(null);
    const r = await api("/me/deletion/cancel", { method: "POST" });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable ? "MyShopEdge could not be reached, so the deletion still stands." : (r.data?.detail ?? "The deletion was not cancelled."));
      return;
    }
    router.push("/shops");
  }

  return (
    <div className="stack">
      {error && <p className="form-error" role="alert">{error}</p>}
      <p>
        <button className="btn btn--primary btn--block" onClick={cancel} disabled={busy} data-testid="cancel-deletion">
          {busy ? "Cancelling" : "Keep my account"}
        </button>
      </p>
    </div>
  );
}
