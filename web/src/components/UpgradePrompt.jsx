/**
 * The upgrade prompt, shown in the page where a plan's feature was asked for. Built 10 October
 * 2026 from the owner's pricing document, which asks that every prompt state the monthly
 * price, the trial or subscription status, the capability it unlocks, an action to choose the
 * plan and a "Not now". It is a card in the page and never a modal, so ordinary navigation is
 * never blocked.
 *
 * The price and the status are read from the service, so nothing here holds a price.
 */

import Link from "next/link";
import { api, fetchPlans, formatDate, formatMoney } from "@/lib/api";
import { PLAN_NAMES, PROMPTS, changePlanHref } from "@/lib/upgrade";
import { NotNow } from "./NotNow";

/**
 * @param {import("@/lib/api-types").components["schemas"]["Subscription"] | null} sub
 * @returns {string | null}
 */
function statusLine(sub) {
  if (!sub || !sub.plan) return null;
  const name = PLAN_NAMES[sub.plan] ?? sub.plan;
  if (sub.status === "trialing" && sub.trial_ends_at) {
    return `You are on the ${name} plan's free trial, which ends on ${formatDate(sub.trial_ends_at)}.`;
  }
  if (sub.status === "active" && sub.current_period_end) {
    return sub.cancel_at_period_end
      ? `You are on the ${name} plan, which ends on ${formatDate(sub.current_period_end)}.`
      : `You are on the ${name} plan, which renews on ${formatDate(sub.current_period_end)}.`;
  }
  if (sub.status === "past_due") return `You are on the ${name} plan, and its last payment did not go through.`;
  return null;
}

/**
 * @param {{ feature: string, plan: string, back?: string, compact?: boolean }} props
 */
export async function UpgradePrompt({ feature, plan, back = "/shops", compact = false }) {
  const [payload, subRes] = await Promise.all([
    fetchPlans(),
    api("/billing/subscription", { cache: "no-store" }),
  ]);
  const target = payload?.plans.find((p) => p.slug === plan) ?? null;
  const sub = subRes.ok ? subRes.data : null;
  const name = PLAN_NAMES[plan] ?? plan;
  const Heading = compact ? "h2" : "h1";
  return (
    <section className={compact ? "card upgrade" : "state upgrade"} data-testid="upgrade-prompt" data-feature={feature}>
      <Heading>{PROMPTS[feature] ?? `This comes with the ${name} plan.`}</Heading>
      {target ? (
        <p data-testid="upgrade-price">
          {name} is {formatMoney(target.price)} a month and covers up to {target.order_limit.toLocaleString("en-GB")} orders a month.
          VAT is not currently charged.
        </p>
      ) : (
        <p>The {name} plan&apos;s price could not be loaded just now.</p>
      )}
      {statusLine(sub) && <p data-testid="upgrade-status">{statusLine(sub)}</p>}
      <p className="upgrade__actions">
        <Link className="btn btn--primary" href={changePlanHref(plan, back)} data-testid="upgrade-choose">
          Choose {name}
        </Link>{" "}
        <NotNow fallback={back} />
      </p>
    </section>
  );
}
