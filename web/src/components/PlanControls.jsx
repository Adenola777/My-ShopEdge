"use client";

/**
 * Stopping the plan renewing, turning it back on, and the way to change the card. Shown on
 * S41 Profile and plan while the plan is live. Added 8 October 2026: the billing screens said
 * a seller could cancel and change the card "in Settings", and Settings had neither.
 *
 * Renewal goes through updateSubscription, which tells Stripe. Nothing is refunded, and a
 * trial that is set not to renew ends without the first payment being taken.
 *
 * Since 11 October 2026 a plan on Annual, billed monthly owes the twelve payments of its term
 * (A38.6). Stopping renewal during a term ends the plan on the term's last day, so the seller
 * is told that the payments left are still taken and on which day the plan ends.
 */

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, formatDate } from "@/lib/api";

/**
 * @param {{ sub: import("@/lib/api-types").components["schemas"]["Subscription"] }} props
 */
export function PlanControls({ sub }) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  const trial = sub.status === "trialing";
  const ends = formatDate(sub.ends_at ?? (trial ? sub.trial_ends_at : sub.current_period_end) ?? "");
  // A running twelve-payment term, outside the trial (A38.6).
  const term = !trial && sub.cycle === "annual_monthly" && sub.commitment_ends_at
    ? formatDate(sub.commitment_ends_at) : null;

  /** @param {boolean} stop */
  async function setRenewal(stop) {
    setBusy(true);
    setError(null);
    const r = await api("/billing/subscription", {
      method: "PATCH",
      body: JSON.stringify({ cancel_at_period_end: stop }),
    });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable
        ? "MyShopEdge could not be reached, so nothing was changed."
        : (r.data?.detail ?? "Nothing was changed. Please try again."));
      return;
    }
    setConfirming(false);
    router.refresh();
  }

  return (
    <div className="plan-controls" data-testid="plan-controls">
      {sub.cancel_at_period_end ? (
        <>
          <p className="card__why">
            {trial
              ? `Your plan will not start. The trial ends on ${ends} and nothing will be charged.`
              : term
                ? `Your plan will end on ${ends}, after the last of its twelve monthly payments, and will not renew.`
                : `Your plan will end on ${ends} and will not renew.`}
          </p>
          <p>
            <button type="button" className="btn btn--primary btn--block" disabled={busy}
              onClick={() => setRenewal(false)} data-testid="plan-keep">
              {busy ? "One moment" : "Keep my plan"}
            </button>
          </p>
        </>
      ) : confirming ? (
        <div className="confirm" role="group" aria-labelledby="stop-renewal-title">
          <p id="stop-renewal-title">
            <strong>
              {trial
                ? `If you stop the plan now, your trial ends on ${ends} and nothing is charged.`
                : term
                  ? `Your plan is on Annual, billed monthly, so its twelve payments run until ${term}. If you stop renewal now, the monthly payments left are still taken and your plan ends on ${term}.`
                  : `If you stop renewal now, your plan ends on ${ends}. Nothing is refunded for the time already paid.`}
            </strong>
          </p>
          <p className="card__why">Your shops and figures stay. You can turn renewal back on here until that date.</p>
          <p>
            <button type="button" className="btn btn--primary btn--block" disabled={busy}
              onClick={() => setRenewal(true)} data-testid="plan-stop-confirm">
              {busy ? "One moment" : trial ? "Stop the plan" : "Stop renewal"}
            </button>
          </p>
          <p>
            <button type="button" className="btn btn--quiet btn--block" disabled={busy}
              onClick={() => setConfirming(false)}>
              Keep my plan
            </button>
          </p>
        </div>
      ) : (
        <p>
          {term ? (
            <span className="card__why" style={{ display: "block" }} data-testid="plan-term">
              Annual, billed monthly: twelve monthly payments, running until {term}.
            </span>
          ) : null}
          <button type="button" className="btn btn--quiet btn--block"
            onClick={() => setConfirming(true)} data-testid="plan-stop">
            {trial ? "Stop the plan before the trial ends" : "Stop renewal"}
          </button>
        </p>
      )}
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      <p>
        <Link className="btn btn--quiet btn--block" href="/billing/card" data-testid="plan-change-card">
          Change card
        </Link>
      </p>
    </div>
  );
}
