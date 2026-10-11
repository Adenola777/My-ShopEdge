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
import { NOTHING_CHANGED, apiProblem } from "@/components/ApiProblem";
import { TaxProfileForm } from "@/components/SetupForms";

export const metadata = { title: "Business details" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function TaxProfilePage({ params }) {
  const { shopId } = await params;
  const r = await api("/tax-profile", { cache: "no-store" });
  // Until 9 October 2026 a failed read drew the form with blank answers, and saving it would
  // have replaced the stored details. The form is now shown only over details that loaded.
  const problem = apiProblem(r, { what: "your business details", note: NOTHING_CHANGED });
  if (problem) return problem;
  return (
    <section data-testid="tax-profile-screen">
      <header className="page-head">
        <h1>Business details</h1>
        <p>Optional. Adds your VAT and tax dates.</p>
      </header>
      <TaxProfileForm shopId={shopId} initial={r.data} />
      <p className="footnote">
        Sell elsewhere too? <Link href={`/shops/${shopId}/other-sales`}>Add other-channel sales</Link>. Not tax advice.
      </p>
    </section>
  );
}
