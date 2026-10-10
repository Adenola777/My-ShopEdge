/**
 * S23 Export (A3, revised by A18.6). Built 29 September 2026 on createExport and getExport.
 * Three kinds only: month summary, ledger and transactions, because A18.6 cut the accountant
 * feed and rules that the screen must not mention it. The file builds in the background and
 * the screen says the seller can leave. Since 9 October 2026 the screen also sets up, pauses and
 * removes scheduled exports (MON-8).
 *
 * Since 10 October 2026 the plan decides what the page offers (entitlements.py): Starter is
 * shown the Growth prompt in place of the form, Growth the form without the recent files,
 * and a prompt for Pro in place of the scheduled exports.
 */

import Link from "next/link";
import { redirect } from "next/navigation";
import { api, fetchShop } from "@/lib/api";
import { apiProblem, NOTHING_CHANGED } from "@/components/ApiProblem";
import { ExportForm, ScheduledExports } from "@/components/SetupForms";
import { UpgradePrompt } from "@/components/UpgradePrompt";

export const metadata = { title: "Export your figures" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function ExportPage({ params }) {
  const { shopId } = await params;
  // A read that proves the shop is the caller's before the form is offered.
  const [check, subRes] = await Promise.all([
    fetchShop(shopId, "/alert-settings"),
    api("/billing/subscription", { cache: "no-store" }),
  ]);
  const problem = apiProblem(check, { what: "this shop", note: NOTHING_CHANGED });
  if (problem) return problem;
  // The service checks the plan again on every export call; this only chooses what to offer.
  // When the subscription cannot be read, the form is offered and the service decides.
  const features = subRes.ok ? (subRes.data?.features ?? []) : null;
  const has = (/** @type {string} */ f) => features === null || features.includes(f);
  // With no trial started the seller is taken to the plan page, as every figure page does (A36).
  if (subRes.ok && subRes.data?.status === "none") redirect("/billing");
  // An ended plan reads but makes no new files (A36), whatever plan it was.
  if (subRes.ok && subRes.data?.status === "canceled") {
    return (
      <section className="state" data-testid="plan-ended">
        <h1>Your plan has ended.</h1>
        <p>Your figures can still be read, but no new file can be built. Choose a plan to export again.</p>
        <p><a className="btn btn--primary" href="/billing">Choose a plan</a></p>
      </section>
    );
  }
  if (!has("exports")) {
    return <UpgradePrompt feature="exports" plan="growth" back={`/shops/${shopId}/money`} />;
  }
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/London" }).format(new Date());
  return (
    <section data-testid="export-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/money`}>Where the money went</Link></p>
        <h1>Exports</h1>
        <p>This page builds an Excel or CSV file of your figures. A month summary has the same totals as Where the money went for the same period.</p>
      </header>
      <ExportForm shopId={shopId} today={today} history={has("export_history")} />
      {has("scheduled_exports") ? (
        <ScheduledExports shopId={shopId} />
      ) : (
        <UpgradePrompt feature="scheduled_exports" plan="pro" back={`/shops/${shopId}/money`} compact />
      )}
    </section>
  );
}
