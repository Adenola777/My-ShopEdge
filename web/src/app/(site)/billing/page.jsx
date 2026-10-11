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
import { CYCLES, priceFor } from "@/lib/plans";
import { STACK_CONFIGURED, currentUser } from "@/lib/stack";

import { PaymentForm } from "./PaymentForm";

export const metadata = { title: "Your plan" };

export const dynamic = "force-dynamic";

/** @param {{ searchParams: Promise<{ plan?: string, cycle?: string }> }} props */
export default async function BillingPage({ searchParams }) {
  const query = await searchParams;
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
  // A cancelled account may start again (`start_trial` refuses only a live plan), so an ended
  // plan is shown the plans rather than told there is nothing to choose.
  if (status && status !== "none" && status !== "canceled") {
    return (
      <section className="billing" data-testid="billing-current">
        <h1>{status === "trialing" ? "Your free trial is running." : status === "active" ? "Your plan is active." : status === "past_due" ? "Your last payment did not go through." : "Your plan is being set up."}</h1>
        <p>{status === "past_due" ? "Your figures stay open to you while it is sorted." : "You can move to another plan here."}</p>
        {status === "past_due" && <p><Link href="/billing/payment-failed" data-testid="payment-failed-link">What a failed payment means</Link></p>}
        {status === "past_due" && <p><Link className="btn btn--quiet" href="/billing/card">Use a different card</Link></p>}
        <Link className="btn btn--primary" href="/shops">Go to your shop</Link>{" "}
        <Link className="btn btn--quiet" href="/pricing" data-testid="billing-change-plan">Change plan</Link>
      </section>
    );
  }

  // A38: the plan and the cycle are chosen in the cart on Plans and pricing. Without them, or
  // for Explorer, which needs no checkout, the seller goes there.
  const payload = await fetchPlans();
  const plan = payload?.plans.find((p) => p.slug === query.plan && !p.free);
  const cycle = /** @type {"annual" | "annual_monthly" | "monthly"} */ (
    CYCLES.includes(/** @type {any} */ (query.cycle)) ? query.cycle : payload?.default_cycle ?? "annual");
  if (payload && !plan) redirect("/pricing");

  if (!payload || !plan) {
    return (
      <section className="billing">
        <h1>We cannot show the plans right now.</h1>
        <p>
          The plans could not be loaded from MyShopEdge, so checkout cannot open yet and
          nothing has been charged. Try again in a few minutes.
        </p>
        <p><a className="btn btn--primary" href="/pricing">Try again</a></p>
      </section>
    );
  }

  // Until the owner approves the prices, no cycle has a Stripe price, so checkout says so
  // and nothing is started (A38.3).
  if (!priceFor(plan, cycle)?.available) {
    return (
      <section className="state" data-testid="checkout-closed">
        <h1>Secure checkout opens soon</h1>
        <p>{plan.name} cannot be bought just yet. Nothing has been started and nothing has been charged.</p>
        <p><a className="btn btn--primary" href="/pricing">Back to plans</a></p>
      </section>
    );
  }

  const { trial_days: trialDays } = payload;
  // An estimate until Stripe creates the subscription, then PaymentForm shows Stripe's own
  // trial end. It is worked out in London time and carries the year.
  const trialEnds = new Date(Date.now() + trialDays * 86_400_000).toLocaleDateString(
    "en-GB",
    { timeZone: "Europe/London", day: "numeric", month: "long", year: "numeric" },
  );

  // A36 (10 October 2026): until a trial starts the shop stays connected and its figures stay
  // closed, so the page names the shop, says its figures are being prepared, and offers
  // Disconnect beside the plans, as the brief's "Connection without subscription" asks.
  /** @type {{ id: string, shop_name?: string | null }[]} */
  const shops = shopsRes.ok ? shopsRes.data?.shops ?? [] : [];
  // A plan chosen but no trial started means the card step was left unfinished: the
  // subscription row exists, still incomplete, which getSubscription reports as none with a plan.
  const abandoned = status === "none" && Boolean(subRes.ok && subRes.data?.plan);
  // The whole flow lives in PaymentForm now: the plan cards are the chooser, so the heading,
  // the cards and the trust footer move inside it and change with the step the seller is on.
  return (
    <section className="billing">
      {shops.length > 0 && (
        <div className="card billing__shops" data-testid="billing-connected">
          {shops.map((shop) => (
            <ul className="rows" key={shop.id}>
              <li><span>Connected shop</span><strong>{shop.shop_name ?? "Your TikTok Shop"}</strong></li>
              <li><span>Status</span><strong>{status === "canceled" ? "Connected, plan ended" : "Connected, trial not started"}</strong></li>
            </ul>
          ))}
          {abandoned && (
            <p data-testid="billing-abandoned">
              <strong>No changes were made.</strong> Your TikTok Shop is connected, and you can start
              your 30-day trial whenever you are ready. Choose your plan below to resume.
            </p>
          )}
          <p className="card__why">
            {status === "canceled"
              ? "Your figures can still be read. Choose a plan to change, export or update them again."
              : "We are preparing your shop figures while you choose your plan."}
          </p>
          <p>
            <Link className="btn btn--quiet" href={`/shops/${shops[0]?.id}/settings/disconnect`} data-testid="billing-disconnect">
              Disconnect shop
            </Link>
          </p>
        </div>
      )}
      <PaymentForm plan={plan} cycle={cycle} trialDays={trialDays} trialEnds={trialEnds} ended={status === "canceled"} />
    </section>
  );
}
