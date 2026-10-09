/**
 * S3 Product costs choice, drawn to wireframe sheet 03 as A15.4 amended it: the three cards
 * are cut and the choices are buttons, with the reassurance kept as a footnote under them.
 * Built 29 September 2026. A14.2 puts it after the plan and before the tax profile.
 */

import Link from "next/link";

export const metadata = { title: "Your product costs" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function CostsChoicePage({ params }) {
  const { shopId } = await params;
  const base = `/shops/${shopId}/setup`;
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
