/**
 * Plans and pricing, A38 (11 October 2026). Open to anybody: a signed-out visitor sees the four
 * plans with "Get started free" and "Buy now", and a signed-in seller also sees their current
 * plan, the upgrade banner and buttons that follow it. The plans and prices are the service's.
 *
 * `?plan=growth&cycle=monthly` opens that plan's cart on arrival, which is where every upgrade
 * prompt in the app leads.
 */

import { api, fetchPlans } from "@/lib/api";
import { CYCLES } from "@/lib/plans";
import { currentUser } from "@/lib/stack";
import { Pricing } from "@/components/Pricing";

export const metadata = { title: "Plans and pricing" };
export const dynamic = "force-dynamic";

/** @param {{ searchParams: Promise<Record<string, string>> }} props */
export default async function PricingPage({ searchParams }) {
  const query = await searchParams;
  const signedIn = Boolean(await currentUser());
  const [payload, subRes, meRes, shopsRes] = await Promise.all([
    fetchPlans(),
    signedIn ? api("/billing/subscription", { cache: "no-store" }) : Promise.resolve(null),
    signedIn ? api("/me", { cache: "no-store" }) : Promise.resolve(null),
    signedIn ? api("/shops", { cache: "no-store" }) : Promise.resolve(null),
  ]);

  if (!payload) {
    return (
      <section className="state">
        <h1>The plans cannot be shown just now.</h1>
        <p>Nothing has been charged. Try again in a few minutes.</p>
        <p><a className="btn btn--primary" href="/pricing">Try again</a></p>
      </section>
    );
  }

  const shopId = shopsRes?.ok ? shopsRes.data?.shops?.[0]?.id : null;
  const cycle = CYCLES.includes(/** @type {any} */ (query.cycle)) ? /** @type {any} */ (query.cycle) : null;
  return (
    <Pricing
      plans={payload.plans}
      defaultCycle={payload.default_cycle}
      sub={subRes?.ok ? subRes.data : null}
      email={meRes?.ok ? meRes.data?.email ?? null : null}
      signedIn={signedIn && Boolean(subRes?.ok)}
      initialPlan={query.plan ?? null}
      initialCycle={cycle}
      manageHref={shopId ? `/shops/${shopId}/settings/profile` : "/billing"}
    />
  );
}
