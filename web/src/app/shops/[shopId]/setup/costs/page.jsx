/**
 * S3 Product costs choice, drawn to wireframe sheet 03 as A15.4 amended it: the three cards
 * are cut and the choices are buttons, with the reassurance kept as a footnote under them.
 * Built 29 September 2026. A14.2 puts it after the plan and before the tax profile.
 *
 * Starter has no product costs (entitlements.py, 10 October 2026). A Starter seller who
 * reaches this step while setting up goes on to the tax profile, because the pricing ruling
 * says no upgrade prompt interrupts setting up.
 */

import Link from "next/link";
import { redirect } from "next/navigation";
import { api } from "@/lib/api";

export const metadata = { title: "Your product costs" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function CostsChoicePage({ params }) {
  const { shopId } = await params;
  const base = `/shops/${shopId}/setup`;
  const sub = await api("/billing/subscription", { cache: "no-store" });
  if (sub.ok && Array.isArray(sub.data?.features) && !sub.data.features.includes("costs")) {
    redirect(`${base}/tax`);
  }
  return (
    <section data-testid="costs-choice">
      <header className="page-head">
        <h1>Do you have your product costs?</h1>
        <p>Costs are optional, and you can add them later.</p>
      </header>
      <div className="stack">
        <Link className="btn btn--primary btn--block" href={`${base}/costs/upload`} data-testid="choose-upload">Yes, in Excel or CSV</Link>
        <Link className="btn btn--quiet btn--block" href={`${base}/costs/manual`} data-testid="choose-manual">Yes, I will type them in</Link>
        <Link className="btn btn--quiet btn--block" href={`${base}/tax`} data-testid="choose-later">Skip costs for now</Link>
        <p className="footnote">Without costs you see your net proceeds. With costs you see your gross profit. MyShopEdge shows you where a missing cost leaves a figure out.</p>
      </div>
    </section>
  );
}
