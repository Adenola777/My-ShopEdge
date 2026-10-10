/**
 * S35 Continue setting up (A14). Built 29 September 2026.
 *
 * A seller who left during onboarding and came back sees what is done, what is left, and one
 * action that resumes at the first step left. A14 rules that a completed step is never
 * restarted, so a connected shop is never offered the connection again. The sync is shown as
 * the service reports it.
 */

import Link from "next/link";
import { api, fetchShop } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";

export const metadata = { title: "Continue setting up" };

/** The part of the shop being read, in words rather than its code. */
/** @type {Record<string, string>} */
const DOMAIN_WORDS = { orders: "orders", returns: "returns", finance: "payouts" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function SetupPage({ params }) {
  const { shopId } = await params;
  const [sync, costs, tax, sub] = await Promise.all([
    fetchShop(shopId, "/sync"),
    fetchShop(shopId, "/costs"),
    api("/tax-profile", { cache: "no-store" }),
    api("/billing/subscription", { cache: "no-store" }),
  ]);
  // Starter has no product costs (entitlements.py, 10 October 2026), so its checklist has no
  // costs step, and it is not shown an upgrade prompt in the middle of setting up.
  const costsOnPlan = !(costs.status === 403 && costs.data?.code === "plan_upgrade_required");
  const problem = costsOnPlan ? apiProblem(costs, { what: "your set-up" }) : null;
  if (problem) return problem;

  const skus = costsOnPlan ? costs.data.skus ?? [] : [];
  const costed = skus.filter((/** @type {any} */ s) => s.cost).length;
  /** @type {any[]} */
  const domains = sync.ok ? sync.data?.domains ?? [] : [];
  const synced = domains.length > 0 && domains.every((d) => d.status === "completed");
  const failedDomain = domains.find((d) => d.status === "failed" || d.status === "needs_reconnect");
  const part = failedDomain ? DOMAIN_WORDS[failedDomain.domain] ?? "shop" : "";
  // A failed part is tried again by the next daily read; a part that needs reconnecting is
  // not, so the two are worded apart.
  const syncNote = !sync.ok ? "Not known right now"
    : failedDomain?.status === "needs_reconnect" ? `Stopped while reading your ${part}. Reconnect your shop to carry on.`
    : failedDomain ? `Stopped while reading your ${part}. MyShopEdge tries again at the next daily read.`
    : synced ? undefined : "Still running";
  const products = `${skus.length} ${skus.length === 1 ? "product" : "products"}`;
  // Each step is named as the thing to do, and carries its own action. A request that failed
  // reads as not known rather than as left to do, so a paying seller is not sent to the plans.
  /** @type {{ label: string, action: string, done: boolean, known: boolean, note?: string, href: string }[]} */
  const steps = [
    { label: "Connect your shop", action: "See your shop connection", done: true, known: true, href: `/shops/${shopId}/settings` },
    { label: "Read your shop's history", action: "See your shop's progress", done: synced, known: sync.ok, note: syncNote, href: `/shops/${shopId}/sync` },
    { label: "Choose a plan", action: "Choose a plan", done: Boolean(sub.ok && sub.data?.status && sub.data.status !== "none"), known: sub.ok,
      note: sub.ok ? undefined : "Not known right now", href: "/billing" },
    ...(costsOnPlan ? [{ label: "Add product costs", action: "Add product costs", done: costed > 0, known: true,
      note: `${costed} of ${products} ${costed === 1 ? "has" : "have"} a cost`, href: `/shops/${shopId}/setup/costs` }] : []),
    { label: "Tell us about your business", action: "Tell us about your business", done: Boolean(tax.ok && tax.data?.completed), known: tax.ok,
      note: tax.ok ? undefined : "Not known right now", href: `/shops/${shopId}/setup/tax` },
  ];
  const next = steps.find((s) => s.known && !s.done);

  return (
    <section data-testid="setup-screen">
      <header className="page-head">
        <h1>Continue setting up</h1>
        <p>Pick up where you left off. Nothing you have done is repeated.</p>
      </header>
      <div className="card">
        <ul className="rows">
          {steps.map((s) => (
            <li key={s.label}>
              <span>{s.label}{s.note && <div className="rows__sub">{s.note}</div>}</span>
              <strong className={s.done ? "chip chip--good" : "chip chip--quiet"}>{s.done ? "Done" : s.known ? "Left to do" : "Not known"}</strong>
            </li>
          ))}
        </ul>
      </div>
      <p>
        {next
          ? <Link className="btn btn--primary btn--block" href={next.href} data-testid="setup-continue">{next.action}</Link>
          : <Link className="btn btn--primary btn--block" href={`/shops/${shopId}/today`} data-testid="setup-continue">Go to Today</Link>}
      </p>
      {next && <p><Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/today`}>Go to Today for now</Link></p>}
    </section>
  );
}
