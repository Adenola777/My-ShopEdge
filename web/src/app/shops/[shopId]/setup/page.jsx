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

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function SetupPage({ params }) {
  const { shopId } = await params;
  const [sync, costs, tax, sub] = await Promise.all([
    fetchShop(shopId, "/sync"),
    fetchShop(shopId, "/costs"),
    api("/tax-profile", { cache: "no-store" }),
    api("/billing/subscription", { cache: "no-store" }),
  ]);
  const problem = apiProblem(costs, { what: "your set-up" });
  if (problem) return problem;

  const skus = costs.data.skus ?? [];
  const costed = skus.filter((/** @type {any} */ s) => s.cost).length;
  /** @type {any[]} */
  const domains = sync.ok ? sync.data?.domains ?? [] : [];
  const synced = domains.length > 0 && domains.every((d) => d.status === "completed");
  const failedDomain = domains.find((d) => d.status === "failed" || d.status === "needs_reconnect");
  const syncNote = !sync.ok ? "Not known right now"
    : failedDomain ? `Stopped on ${failedDomain.domain}`
    : synced ? undefined : "Still running";
  const steps = [
    { label: "TikTok Shop connected", done: true, href: `/shops/${shopId}/settings` },
    { label: "Your shop's history read", done: synced, note: syncNote, href: `/shops/${shopId}/sync` },
    { label: "Plan chosen", done: sub.ok && sub.data?.status && sub.data.status !== "none", href: "/billing" },
    { label: "Product costs", done: costed > 0, note: `${costed} of ${skus.length} variants have a cost`, href: `/shops/${shopId}/setup/costs` },
    { label: "About your business", done: tax.ok && tax.data?.completed, href: `/shops/${shopId}/setup/tax` },
  ];
  const next = steps.find((s) => !s.done);

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
              <strong className={s.done ? "chip chip--good" : "chip chip--quiet"}>{s.done ? "Done" : "Left to do"}</strong>
            </li>
          ))}
        </ul>
      </div>
      <p>
        {next
          ? <Link className="btn btn--primary btn--block" href={next.href} data-testid="setup-continue">Continue: {next.label.toLowerCase()}</Link>
          : <Link className="btn btn--primary btn--block" href={`/shops/${shopId}/today`} data-testid="setup-continue">Go to Today</Link>}
      </p>
      {next && <p><Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/today`}>Go to Today for now</Link></p>}
    </section>
  );
}
