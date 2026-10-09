/**
 * S23 Export (A3, revised by A18.6). Built 29 September 2026 on createExport and getExport.
 * Three kinds only: month summary, ledger and transactions, because A18.6 cut the accountant
 * feed and rules that the screen must not mention it. The file builds in the background and
 * the screen says the seller can leave. Since 9 October 2026 the screen also sets up, pauses and
 * removes scheduled exports (MON-8).
 */

import Link from "next/link";
import { fetchShop } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { ExportForm, ScheduledExports } from "@/components/SetupForms";

export const metadata = { title: "Export" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function ExportPage({ params }) {
  const { shopId } = await params;
  // A read that proves the shop is the caller's before the form is offered.
  const check = await fetchShop(shopId, "/alert-settings");
  const problem = apiProblem(check, { what: "this shop" });
  if (problem) return problem;
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/London" }).format(new Date());
  return (
    <section data-testid="export-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/money`}>Money</Link></p>
        <h1>Export</h1>
        <p>An Excel or CSV file whose totals equal the screen.</p>
      </header>
      <ExportForm shopId={shopId} today={today} />
      <ScheduledExports shopId={shopId} />
    </section>
  );
}
