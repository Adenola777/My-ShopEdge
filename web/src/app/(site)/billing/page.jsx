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
import { api, fetchPlans } from "@/lib/api";
import { STACK_CONFIGURED, currentUser } from "@/lib/stack";

import { PaymentForm } from "./PaymentForm";

export const metadata = { title: "Your plan" };

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
      <section className="billing" data-testid="billing-current">
        <h1>{status === "trialing" ? "Your free trial is running." : status === "active" ? "Your plan is active." : status === "past_due" ? "Your last payment did not go through." : status === "canceled" ? "Your plan has ended." : "Your plan is being set up."}</h1>
        <p>{status === "past_due" ? "Your figures stay open to you while it is sorted." : "There is nothing to choose here now."}</p>
        {status === "past_due" && <p><Link href="/billing/payment-failed" data-testid="payment-failed-link">What a failed payment means</Link></p>}
        <Link className="btn btn--primary" href="/shops">Go to your shop</Link>
      </section>
    );
  }

  const payload = await fetchPlans();

  if (!payload) {
    return (
      <section className="billing">
        <h1>We cannot show the plans right now.</h1>
        <p>
          The plans could not be loaded from MyShopEdge, so no plan can be chosen yet and
          nothing has been charged. Try again in a few minutes.
        </p>
        <p><a className="btn btn--primary" href="/billing">Try again</a></p>
      </section>
    );
  }

  const { trial_days: trialDays, plans } = payload;
  const trialEnds = new Date(Date.now() + trialDays * 86_400_000).toLocaleDateString(
    "en-GB",
    { day: "numeric", month: "long" },
  );

  // The whole flow lives in PaymentForm now: the plan cards are the chooser, so the heading,
  // the cards and the trust footer move inside it and change with the step the seller is on.
  return (
    <section className="billing">
      <PaymentForm plans={plans} trialDays={trialDays} trialEnds={trialEnds} />
    </section>
  );
}
