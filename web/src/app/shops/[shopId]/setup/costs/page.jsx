/**
 * S3 Product costs choice, drawn to wireframe sheet 03 as A15.4 amended it: the three cards
 * are cut and the choices are buttons. Built 29 September 2026.
 *
 * Since A36 step 2 (10 October 2026) this is the brief's section 7, the product cost
 * decision. It comes after the first figures rather than before them (A36.1 item 3), and its
 * Skip leads to Overview, not to the tax profile. A Starter seller, whose plan holds no
 * product costs (A35), is shown the Growth prompt here: the first figures have already been
 * seen, which is when the pricing ruling allows a prompt.
 */

import Link from "next/link";
import { api } from "@/lib/api";
import { UpgradePrompt } from "@/components/UpgradePrompt";

export const metadata = { title: "Your product costs" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function CostsChoicePage({ params }) {
  const { shopId } = await params;
  const base = `/shops/${shopId}/setup`;
  const sub = await api("/billing/subscription", { cache: "no-store" });
  if (sub.ok && Array.isArray(sub.data?.features) && !sub.data.features.includes("costs")) {
    return <UpgradePrompt feature="costs" plan="growth" back={`/shops/${shopId}/today`} />;
  }
  return (
    <section data-testid="costs-choice">
      <header className="page-head">
        <h1>Do you have your product costs?</h1>
        <p>Costs are optional, and you can add them later.</p>
      </header>
      <div className="stack">
        <div className="card">
          <p>Without costs you see net proceeds.</p>
          <p>With costs you see gross profit and gross margin.</p>
        </div>
        <Link className="btn btn--primary btn--block" href={`${base}/costs/upload`} data-testid="choose-upload">Yes, in Excel or CSV</Link>
        <Link className="btn btn--quiet btn--block" href={`${base}/costs/manual`} data-testid="choose-manual">Yes, I will type them in</Link>
        <Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/today`} data-testid="choose-later">Skip costs for now</Link>
      </div>
    </section>
  );
}
