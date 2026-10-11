/**
 * Change plan. Since A38 (11 October 2026) a plan is changed from Plans and pricing, whose cart
 * states the plan, the billing cycle and the price before anything changes. This address is
 * kept so that links already sent still work, and it opens that cart.
 */

import { redirect } from "next/navigation";

/** @param {{ searchParams: Promise<{ plan?: string, cycle?: string }> }} props */
export default async function ChangePlanPage({ searchParams }) {
  const { plan, cycle } = await searchParams;
  const q = new URLSearchParams();
  if (plan) q.set("plan", plan);
  if (cycle) q.set("cycle", cycle);
  redirect(`/pricing${q.size ? `?${q}` : ""}`);
}
