/**
 * S33. Choose a plan and verify your card.
 *
 * This screen sits after the TikTok Shop connection in the onboarding order, because a
 * seller who cannot connect a shop has nothing to pay for.
 *
 * The plans and their prices come from the API. Nothing on this page holds a price.
 *
 * It is reached from S2 First sync and from `/shops` while the account has no plan
 * (`lib/onboarding.js`). Until 28 September nothing linked here.
 */

import Link from "next/link";
import { redirect } from "next/navigation";
import { api, fetchPlans, formatMoney } from "@/lib/api";
import { STACK_CONFIGURED, currentUser } from "@/lib/stack";

/** @typedef {import("@/lib/api-types").components["schemas"]["Plan"]} Plan */
import { PaymentForm } from "./PaymentForm";

export const metadata = { title: "Start your free trial" };

export const dynamic = "force-dynamic";

export default async function BillingPage() {
  // Found on 28 September by walking the journey signed out: this page opened for anybody
  // and told them their shop was connected. It now checks both claims before making them.
  if (STACK_CONFIGURED && !(await currentUser())) redirect("/start");
  const [shopsRes, subRes] = await Promise.all([
    api("/shops", { cache: "no-store" }),
    api("/billing/subscription", { cache: "no-store" }),
  ]);
  if (shopsRes.status === 401) redirect("/start");
  // A14.2: the plan comes after the connection, because a seller with no shop has nothing
  // to pay for.
  if (shopsRes.ok && (shopsRes.data?.shops ?? []).length === 0) redirect("/shops");
  const status = subRes.ok ? subRes.data?.status : null;
  if (status && status !== "none") {
    return (
      <main className="billing" data-testid="billing-current">
        <h1>{status === "trialing" ? "Your free trial is running." : status === "active" ? "Your plan is active." : `Your subscription is ${status.replace("_", " ")}.`}</h1>
        <p>There is nothing to choose here now.</p>
        {status === "past_due" && <p><Link href="/billing/payment-failed" data-testid="payment-failed-link">What a failed payment means</Link></p>}
        <Link className="btn btn--primary" href="/shops">Go to your shop</Link>
      </main>
    );
  }

  const payload = await fetchPlans();

  if (!payload) {
    return (
      <main className="billing">
        <h1>We cannot show the plans right now.</h1>
        <p>
          The plans could not be loaded from MyShopEdge, so no plan can be chosen yet and
          nothing has been charged. Try again in a few minutes.
        </p>
      </main>
    );
  }

  const { trial_days: trialDays, plans } = payload;
  const trialEnds = new Date(Date.now() + trialDays * 86_400_000).toLocaleDateString(
    "en-GB",
    { day: "numeric", month: "long" },
  );

  return (
    <main className="billing">
      <header className="billing__head">
        <h1>Your shop is connected. Choose a plan to start.</h1>
        <p className="billing__lede">
          Every plan begins with {trialDays} days free. We verify your card now and take
          nothing until {trialEnds}. You can cancel before then and you will not be charged.
        </p>
      </header>

      <ol className="plans" aria-label="Plans">
        {plans.map((/** @type {Plan} */ plan) => (
          <li
            key={plan.slug}
            className={plan.highlight ? "plan plan--highlight" : "plan"}
            aria-current={plan.highlight ? "true" : undefined}
          >
            {plan.highlight ? <p className="plan__flag">Most chosen</p> : null}
            <h2 className="plan__name">{plan.name}</h2>
            <p className="plan__strapline">{plan.strapline}</p>
            <p className="plan__price">
              <span className="plan__amount">{formatMoney(plan.price)}</span>
              <span className="plan__period"> a month</span>
            </p>
            <p className="plan__limit">
              Up to {plan.order_limit.toLocaleString("en-GB")} orders a month, and{" "}
              {plan.history_months} months of history.
            </p>
            <ul className="plan__features">
              {plan.features.map((/** @type {string} */ feature) => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>
          </li>
        ))}
      </ol>

      <PaymentForm plans={plans} trialDays={trialDays} />

      <footer className="billing__foot">
        <p>
          Your bank may ask you to confirm the card. That confirmation is what lets us take
          the first payment when the trial ends, so the step cannot be skipped.
        </p>
        <p>
          We store no card details. Stripe holds them and we hold a reference. You can change
          the card or cancel at any time in Settings.
        </p>
      </footer>
    </main>
  );
}
