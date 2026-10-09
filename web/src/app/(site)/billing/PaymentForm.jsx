"use client";

/**
 * S33. Choose a plan and start the free trial.
 *
 * The plan cards are the control. A seller taps a card to choose it, reads a plain summary
 * of what starting the trial means, and moves to the card step in one button. This replaced
 * an earlier layout where the cards only displayed the plans and a separate radio list below
 * them did the choosing; on a phone that list sat far below three full-height cards, so the
 * cards looked like the choice and tapping one did nothing (owner report, 7 October 2026).
 *
 * The flow has two steps at Stripe, and the second is the one that matters.
 *
 *   1. Ask the API for a subscription. It creates one with a trial and an incomplete payment
 *      behaviour, and returns the client secret of a SetupIntent.
 *   2. Confirm that SetupIntent in the browser. This is where the bank may present a
 *      challenge, and where the mandate for later off session charges is recorded.
 *
 * The component never sees a price and never sends one. It sends a plan slug. The plan can
 * be changed freely while choosing; once the card step opens the subscription exists at
 * Stripe, so the choice is fixed from then on (the service hands back the same incomplete
 * subscription regardless of a later slug, so offering a change here would quietly ignore it).
 *
 * @typedef {import("@/lib/api-types").components["schemas"]} Schemas
 * @typedef {Schemas["Plan"]} Plan
 */

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { api, formatMoney } from "@/lib/api";

// Read on 28 September 2026: without NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY the button below used
// to create the subscription at Stripe and only then fail to show the card form, leaving a
// trial with no card. With no key nothing is started. The key is set on Vercel for
// production and preview as of 7 October, so this guard is inert there.
const PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;
const stripePromise = PUBLISHABLE_KEY ? loadStripe(PUBLISHABLE_KEY) : null;

/**
 * `trialEnds` is an estimate made before the subscription exists. Once Stripe has created it,
 * the trial end Stripe returned is shown instead (copy audit of 8 October 2026, row on the
 * trial date). `ended` is true when the seller's earlier plan has ended, because
 * `start_trial` lets a cancelled account start again.
 *
 * @param {{ plans: Plan[], trialDays: number, trialEnds: string, ended?: boolean }} props
 */
export function PaymentForm({ plans, trialDays, trialEnds: estimate, ended = false }) {
  const preferred = plans.find((p) => p.highlight) ?? plans[0];
  const [slug, setSlug] = useState(preferred ? preferred.slug : "");
  const [phase, setPhase] = useState(
    /** @type {"choosing" | "collecting" | "done"} */ ("choosing"),
  );
  const [clientSecret, setClientSecret] = useState(/** @type {string | null} */ (null));
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [busy, setBusy] = useState(false);
  const [stripeTrialEnd, setStripeTrialEnd] = useState(/** @type {string | null} */ (null));
  const trialEnds = stripeTrialEnd ?? estimate;

  // Held for the life of the component so a retry after a dropped connection does not
  // create a second subscription.
  const idempotencyKey = useMemo(() => crypto.randomUUID(), []);

  const chosen = plans.find((p) => p.slug === slug);

  const start = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const { ok, data } = await api("/billing/subscription", {
        method: "POST",
        body: JSON.stringify({ plan: slug }),
        idempotencyKey,
      });
      if (!ok) {
        setError(data?.detail ?? "We could not start the trial. Nobody has been charged. Try again in a moment.");
        return;
      }
      if (data.trial_ends_at) {
        setStripeTrialEnd(
          new Date(data.trial_ends_at).toLocaleDateString("en-GB", {
            timeZone: "Europe/London", day: "numeric", month: "long", year: "numeric",
          }),
        );
      }
      if (data.status === "trialing") {
        setPhase("done");
        return;
      }
      setClientSecret(data.client_secret);
      setPhase("collecting");
    } catch {
      setError("We could not reach the server. Nobody has been charged.");
    } finally {
      setBusy(false);
    }
  }, [slug, idempotencyKey]);

  if (!stripePromise) {
    return (
      <section className="card-step" data-testid="billing-unconfigured">
        <h1>Card payments are temporarily unavailable.</h1>
        <p>Nothing has been started, and nothing has been charged. Please try again shortly.</p>
      </section>
    );
  }

  if (phase === "done") {
    return (
      <section className="card-step card-step--done" aria-live="polite" data-testid="billing-done">
        <h1>Your free trial has started.</h1>
        <p>
          You are on {chosen ? chosen.name : "your plan"} for {trialDays} days. Nothing has
          been charged. We will email you seven days before the first payment on {trialEnds},
          and you can cancel before then in Settings and pay nothing.
        </p>
        <Link className="btn btn--primary btn--block" href="/shops" data-testid="billing-done-continue">
          Go to your shop
        </Link>
      </section>
    );
  }

  return (
    <>
      <header className="billing__head">
        <h1>
          {phase === "collecting"
            ? "Add your card to start the trial."
            : ended
              ? "Your plan has ended. Choose a plan to start again."
              : "Your shop is connected. Start your free trial."}
        </h1>
        <p className="billing__lede">
          Every plan begins with {trialDays} days free, and nothing is taken until{" "}
          {trialEnds}. You can stop the plan in Settings before then, and nothing is charged.
        </p>
      </header>

      {phase === "choosing" ? (
        <section className="card-step">
          <fieldset className="plans" aria-describedby="plan-help">
            <legend className="visually-hidden">Choose your plan</legend>
            {plans.map((/** @type {Plan} */ plan) => {
              const selected = slug === plan.slug;
              const cls =
                "plan plan--selectable" +
                (plan.highlight ? " plan--highlight" : "") +
                (selected ? " plan--selected" : "");
              return (
                <label key={plan.slug} className={cls} data-testid={`plan-${plan.slug}`}>
                  <input
                    type="radio"
                    name="plan"
                    className="plan__radio visually-hidden"
                    value={plan.slug}
                    checked={selected}
                    onChange={() => setSlug(plan.slug)}
                  />
                  <span className="plan__select" aria-hidden="true" />
                  {plan.highlight ? <span className="plan__flag">Most chosen</span> : null}
                  <span className="plan__name">{plan.name}</span>
                  <span className="plan__strapline">{plan.strapline}</span>
                  <span className="plan__price">
                    <span className="plan__amount">{formatMoney(plan.price)}</span>
                    <small> a month after your free trial</small>
                  </span>
                  <span className="plan__limit">
                    Made for up to {plan.order_limit.toLocaleString("en-GB")} orders a month.
                    Nothing stops if you sell more. {plan.history_months} months of history.
                  </span>
                  <span className="plan__features" role="list">
                    {plan.features.map((/** @type {string} */ feature) => (
                      <span className="plan__feature" role="listitem" key={feature}>
                        {feature}
                      </span>
                    ))}
                  </span>
                </label>
              );
            })}
          </fieldset>

          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}

          <div className="plan-cta">
            <p className="plan-cta__summary" id="plan-help">
              {chosen ? (
                <>
                  You chose {chosen.name}. After {trialDays} free days it is{" "}
                  {formatMoney(chosen.price)} a month, and you can change the card or stop the
                  plan at any time in Settings. Your plan is fixed once you continue to the card.
                </>
              ) : (
                <>Choose a plan to continue.</>
              )}
            </p>
            <button
              type="button"
              className="btn btn--primary btn--block"
              onClick={start}
              disabled={busy || !chosen}
              data-testid="billing-continue"
            >
              {busy ? "Setting up your trial" : chosen ? `Continue with ${chosen.name}` : "Continue"}
            </button>
          </div>
        </section>
      ) : null}

      {phase === "collecting" && clientSecret ? (
        <section className="card-step">
          <div className="plan-summary" data-testid="plan-summary">
            <p>
              You are starting <strong>{chosen ? chosen.name : "your plan"}</strong>. Your{" "}
              {trialDays} free days run until {trialEnds}.
            </p>
          </div>
          <Elements
            stripe={stripePromise}
            options={{
              clientSecret,
              appearance: { theme: "flat", variables: { colorPrimary: "#C4400C" } },
            }}
          >
            <ConfirmCard
              planName={chosen ? chosen.name : "your plan"}
              trialDays={trialDays}
              onDone={() => setPhase("done")}
            />
          </Elements>
        </section>
      ) : null}

      <footer className="billing__foot">
        <p>
          Your bank may ask you to confirm the card. That confirmation is what lets us take
          the first payment when the trial ends, so the step cannot be skipped.
        </p>
        <p>
          We store no card details. Stripe holds them and we hold a reference. You can change
          the card or stop the plan at any time in Settings.
        </p>
      </footer>
    </>
  );
}

/**
 * @param {{ planName: string, trialDays: number, onDone: () => void }} props
 */
function ConfirmCard({ planName, trialDays, onDone }) {
  const stripe = useStripe();
  const elements = useElements();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  /** @param {{ preventDefault: () => void }} event */
  async function submit(event) {
    event.preventDefault();
    if (!stripe || !elements) return;
    setBusy(true);
    setError(null);

    // redirect "if_required" keeps the seller on this screen unless their bank insists on
    // a redirect for the authentication challenge.
    const result = await stripe.confirmSetup({
      elements,
      confirmParams: { return_url: `${window.location.origin}/billing/confirmed` },
      redirect: "if_required",
    });

    if (result.error) {
      setError(`${result.error.message ?? "Your bank did not confirm the card."} Nothing has been charged. Check the details or try another card.`);
      setBusy(false);
      return;
    }
    onDone();
  }

  return (
    <form onSubmit={submit} className="card-form">
      <p className="card-form__note">
        We verify the card now and charge nothing today.
      </p>
      <PaymentElement options={{ layout: "tabs" }} />
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      <button type="submit" className="btn btn--primary btn--block" disabled={!stripe || busy}>
        {busy ? "Confirming with your bank" : `Start ${planName} free for ${trialDays} days`}
      </button>
    </form>
  );
}
