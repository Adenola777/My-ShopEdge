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
        <p>This step is optional. It lets MyShopEdge show your VAT and tax dates.</p>
      </header>
      <TaxProfileForm shopId={shopId} initial={r.data} />
      <p className="footnote">
        Sell outside TikTok as well? <Link href={`/shops/${shopId}/other-sales`}>Add those sales month by month</Link> so your progress towards the VAT registration threshold counts them.
        These figures help you plan. They are not tax advice.
      </p>
    </section>
  );
}
