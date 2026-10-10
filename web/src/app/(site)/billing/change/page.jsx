/**
 * Change plan. Added 10 October 2026 with the pricing tiers, because an upgrade prompt needs
 * somewhere to go: until then nothing in the app could change a running plan.
 *
 * The page states the plan now, the plan chosen, its price, and what happens to billing,
 * and the change is made only when the seller presses the button. Nothing changes on
 * arrival, and "Not now" goes back without a change. The service takes the price from its
 * own configuration, never from this page.
 */

import Link from "next/link";
import { redirect } from "next/navigation";
import { api, fetchPlans, formatDate, formatMoney } from "@/lib/api";
import { PLAN_NAMES } from "@/lib/upgrade";
import { STACK_CONFIGURED, currentUser } from "@/lib/stack";

import { ChangePlanForm } from "./ChangePlanForm";

export const metadata = { title: "Change plan" };

export const dynamic = "force-dynamic";

/** Only a path inside the app is followed back, so the link cannot send a seller elsewhere. */
function safeBack(/** @type {string | undefined} */ back) {
  return back && back.startsWith("/") && !back.startsWith("//") ? back : "/shops";
}

/** @param {{ searchParams: Promise<{ plan?: string, back?: string }> }} props */
export default async function ChangePlanPage({ searchParams }) {
  if (STACK_CONFIGURED && !(await currentUser())) redirect("/start");
  const { plan: wanted, back: rawBack } = await searchParams;
  const back = safeBack(rawBack);
  const [payload, subRes] = await Promise.all([
    fetchPlans(),
    api("/billing/subscription", { cache: "no-store" }),
  ]);
  if (subRes.status === 401) redirect("/start");
  const sub = subRes.ok ? subRes.data : null;
  // With no plan running there is nothing to change, so the seller chooses one from the start.
  if (sub && !["trialing", "active", "past_due"].includes(sub.status)) redirect("/billing");

  if (!payload || !sub) {
    return (
      <section className="billing">
        <h1>We cannot show your plan right now.</h1>
        <p>Nothing has been changed. Try again in a few minutes.</p>
        <p><a className="btn btn--primary" href="">Try again</a></p>
      </section>
    );
  }

  const plans = payload.plans;
  const current = plans.find((p) => p.slug === sub.plan) ?? null;
  const chosen = plans.find((p) => p.slug === wanted) ?? null;
  const trial = sub.status === "trialing";

  return (
    <section className="billing" data-testid="change-plan">
      <h1>Change plan</h1>
      <p>
        {current
          ? `You are on the ${current.name} plan at ${formatMoney(current.price)} a month.`
          : "Your current plan could not be named."}{" "}
        {trial && sub.trial_ends_at
          ? `Your free trial ends on ${formatDate(sub.trial_ends_at)}.`
          : sub.current_period_end
            ? `Your plan renews on ${formatDate(sub.current_period_end)}.`
            : ""}
      </p>
      <div className="plan-cards">
        {plans.map((p) => (
          <div key={p.slug} className={`card plan-card${p.slug === chosen?.slug ? " plan-card--chosen" : ""}`} data-testid={`change-plan-${p.slug}`}>
            <h2>
              {p.name}{p.highlight ? <span className="chip chip--good"> Most popular</span> : null}
            </h2>
            <p><strong className="money">{formatMoney(p.price)}</strong> a month</p>
            <p className="card__why">{p.strapline}</p>
            <ul>
              {p.features.map((f) => <li key={f}>{f}</li>)}
            </ul>
            {p.slug === sub.plan ? (
              <p className="chip chip--quiet">Your plan</p>
            ) : (
              <p><Link className="btn btn--quiet btn--block" href={`/billing/change?${new URLSearchParams({ plan: p.slug, back }).toString()}`}>Choose {p.name}</Link></p>
            )}
          </div>
        ))}
      </div>
      {chosen && chosen.slug !== sub.plan ? (
        <div className="card" data-testid="change-plan-confirm">
          <h2>Move to {chosen.name} at {formatMoney(chosen.price)} a month</h2>
          <p>
            {trial
              ? `Nothing is charged today. Your trial still ends on ${formatDate(sub.trial_ends_at ?? "")}, and the first payment is then ${formatMoney(chosen.price)}.`
              : `From today your plan is ${chosen.name}. For the days left in this billing period, Stripe adds the difference between the two prices to your next invoice, or takes it off when the new plan costs less. After that the plan renews at ${formatMoney(chosen.price)} a month.`}
          </p>
          <p className="card__why">VAT is not currently charged. Every plan connects one TikTok Shop.</p>
          <ChangePlanForm plan={chosen.slug} name={chosen.name} back={back} />
        </div>
      ) : null}
      <p><Link className="btn btn--quiet" href={back} data-testid="change-plan-back">{chosen && chosen.slug !== sub.plan ? "Not now" : "Back"}</Link></p>
    </section>
  );
}
