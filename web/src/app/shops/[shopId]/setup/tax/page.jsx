/**
 * S5 Tax profile, drawn to wireframe sheet 04. Built 29 September 2026 on getTaxProfile and
 * putTaxProfile.
 *
 * The sheet also asks for sales outside TikTok per month and the gross income on the last
 * tax return. The contract's TaxProfileInput holds neither. Sales outside TikTok are entered
 * month by month on S24, so the screen links there. The prior year's income is not asked for,
 * because nothing could store it.
 */

import Link from "next/link";
import { api } from "@/lib/api";
import { TaxProfileForm } from "@/components/SetupForms";

export const metadata = { title: "About your business" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function TaxProfilePage({ params }) {
  const { shopId } = await params;
  const r = await api("/tax-profile", { cache: "no-store" });
  return (
    <section data-testid="tax-profile-screen">
      <header className="page-head">
        <h1>About your business</h1>
        <p>Optional. Helps with VAT and tax dates.</p>
      </header>
      <TaxProfileForm shopId={shopId} initial={r.ok ? r.data : null} />
      <p className="footnote">
        Sell outside TikTok as well? <Link href={`/shops/${shopId}/other-sales`}>Add those sales month by month</Link> so the VAT line counts them.
        A guide to help you plan. Not tax advice.
      </p>
    </section>
  );
}
