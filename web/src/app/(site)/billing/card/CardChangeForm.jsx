"use client";

/**
 * Replacing the card the plan charges. Added 8 October 2026.
 *
 * Three steps, the same shape as the trial's card step in PaymentForm: startCardChange
 * returns the client secret of a SetupIntent, the browser confirms it (where the bank may ask
 * the seller to approve the card), and setCard makes the confirmed card the one the plan
 * charges. Nothing is charged at any step. When the bank insists on a redirect, the seller
 * comes back to /billing/card/done, which finishes the third step.
 */

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { api } from "@/lib/api";

const PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;
const stripePromise = PUBLISHABLE_KEY ? loadStripe(PUBLISHABLE_KEY) : null;

/** @param {{ back: string }} props */
export function CardChangeForm({ back }) {
  const [secret, setSecret] = useState(/** @type {string | null} */ (null));
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!stripePromise) return;
    let live = true;
    api("/billing/card", { method: "POST" }).then((r) => {
      if (!live) return;
      if (r.ok) setSecret(r.data.client_secret);
      else setError(r.unreachable
        ? "MyShopEdge could not be reached, so your card was not changed."
        : (r.data?.detail ?? "Your card was not changed. Please try again."));
    });
    return () => { live = false; };
  }, []);

  if (!stripePromise) {
    return (
      <section className="card-step">
        <h1>Changing the card is not available just now.</h1>
        <p>Your card has not been changed. Please try again later.</p>
      </section>
    );
  }

  if (done) {
    return (
      <section className="card-step card-step--done" aria-live="polite" data-testid="card-done">
        <h1>Your new card is saved.</h1>
        <p>Your plan will charge this card from its next payment. Nothing has been charged today.</p>
        <Link className="btn btn--primary btn--block" href={back}>Back to your plan</Link>
      </section>
    );
  }

  return (
    <section className="card-step">
      <h1>Change the card your plan charges.</h1>
      <p className="billing__lede">
        We check the new card with your bank and charge nothing today. Your bank may ask you to
        approve it.
      </p>
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      {secret ? (
        <Elements
          stripe={stripePromise}
          options={{ clientSecret: secret, appearance: { theme: "flat", variables: { colorPrimary: "#C4400C" } } }}
        >
          <ConfirmNewCard onDone={() => setDone(true)} />
        </Elements>
      ) : !error ? (
        <p className="muted" aria-live="polite">Getting the card form ready.</p>
      ) : null}
      <p><Link className="btn btn--quiet btn--block" href={back}>Keep my current card</Link></p>
    </section>
  );
}

/** @param {{ onDone: () => void }} props */
function ConfirmNewCard({ onDone }) {
  const stripe = useStripe();
  const elements = useElements();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const returnUrl = useMemo(
    () => (typeof window === "undefined" ? "" : `${window.location.origin}/billing/card/done`), []);

  /** @param {{ preventDefault: () => void }} event */
  async function submit(event) {
    event.preventDefault();
    if (!stripe || !elements) return;
    setBusy(true);
    setError(null);
    const result = await stripe.confirmSetup({
      elements,
      confirmParams: { return_url: returnUrl },
      redirect: "if_required",
    });
    if (result.error) {
      setError(result.error.message ?? "Your bank did not approve the card, so nothing was changed.");
      setBusy(false);
      return;
    }
    const saved = await saveCard(result.setupIntent?.id);
    if (saved) {
      setError(saved);
      setBusy(false);
      return;
    }
    onDone();
  }

  return (
    <form onSubmit={submit} className="card-form">
      <PaymentElement options={{ layout: "tabs" }} />
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      <button type="submit" className="btn btn--primary btn--block" disabled={!stripe || busy}>
        {busy ? "Checking with your bank" : "Save new card"}
      </button>
    </form>
  );
}

/**
 * The third step, shared with the page a bank redirect returns to.
 *
 * @param {string | undefined} setupIntentId
 * @returns {Promise<string | null>}  An error to show, or null when the card is saved.
 */
export async function saveCard(setupIntentId) {
  if (!setupIntentId) return "Your bank did not finish checking the card, so nothing was changed.";
  const r = await api("/billing/card", {
    method: "PUT",
    body: JSON.stringify({ setup_intent_id: setupIntentId }),
  });
  if (r.ok) return null;
  return r.unreachable
    ? "Your bank approved the card, but MyShopEdge could not be reached to save it. Please try again."
    : (r.data?.detail ?? "Your card was not changed. Please try again.");
}
