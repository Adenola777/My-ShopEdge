/**
 * The upgrade prompt, shown in the page where a plan's feature was asked for. Rewritten
 * 11 October 2026 to the owner's pricing and checkout specification (A38): what the seller
 * gets, what the plan includes, its monthly price with "Cancel anytime", then "Upgrade to
 * <plan>" beside "Maybe later". It is a card in the page and never a modal, so ordinary
 * navigation is never blocked, and it uses no red, because an upgrade is not a fault.
 *
 * The price is read from the service, so nothing here holds a price.
 */

import Link from "next/link";
import { fetchPlans } from "@/lib/api";
import { monthlyLine } from "@/lib/plans";
import { INCLUDES, PLAN_NAMES, PROMPTS, changePlanHref } from "@/lib/upgrade";
import { NotNow } from "./NotNow";

/**
 * @param {{ feature: string, plan: string, back?: string, compact?: boolean }} props
 */
export async function UpgradePrompt({ feature, plan, back = "/shops", compact = false }) {
  const payload = await fetchPlans();
  const target = payload?.plans.find((p) => p.slug === plan);
  const name = PLAN_NAMES[plan] ?? plan;
  const words = PROMPTS[feature] ?? { title: `Available on ${name}` };
  const Heading = compact ? "h2" : "h1";
  const price = monthlyLine(target);
  return (
    <section className={compact ? "card upgrade" : "card upgrade upgrade--page"} data-testid="upgrade-prompt" data-feature={feature}>
      <Heading>{words.title}</Heading>
      {words.lead && <p>{words.lead}</p>}
      <p className="upgrade__includes-label">{name} includes:</p>
      <ul className="upgrade__includes">
        {(INCLUDES[plan] ?? []).map((line) => <li key={line}>{line}</li>)}
      </ul>
      <p className="upgrade__price" data-testid="upgrade-price">
        {price ? `${price} · Cancel anytime` : `The ${name} price could not be loaded just now.`}
      </p>
      <p className="upgrade__actions">
        <Link className="btn btn--primary" href={changePlanHref(plan, back)} data-testid="upgrade-choose">
          Upgrade to {name}
        </Link>{" "}
        <NotNow fallback={back} label="Maybe later" />
      </p>
    </section>
  );
}
