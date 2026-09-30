/**
 * S32 Glossary, from the shared reference rules (TAX-6). It renders whatever `listRules`
 * returns, each term carrying the date its rule was last reviewed and its source, so a
 * seller can see the figure is current rather than trusting it.
 *
 * Written by Emergent AI in `Adenola777/MYSHOPEDGE` (commit 3f1bd43) and brought into this
 * repository on 28 September 2026 at the owner's instruction. See
 * `audit/EMERGENT_review_28_september.md`. Changes on the way in: an amount is formatted by
 * `formatMoney` rather than by its own division, and the empty state uses a card, because
 * this stylesheet has no `state` class.
 */

import { api, formatDate, formatMoney } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";

export const metadata = { title: "Help and glossary" };

/** What each figure on the screens means, in the A8 terms. The rules below it come from the service. */
const TERMS = [
  ["Gross sales (GMV)", "What customers paid for your products, before refunds and before anything TikTok takes."],
  ["Refunds to customers", "Money returned to buyers, in full or in part."],
  ["Net proceeds", "Your sales after refunds, less every fee and deduction TikTok makes."],
  ["Gross profit after returns", "Net proceeds less what the goods you sold cost you, after returned stock is put back or written off. It is before your own running costs and your tax."],
  ["Settlement", "A statement from TikTok and the payout it sends to your bank."],
  ["Sales basis", "Counts money on the day of the sale."],
  ["Cash basis", "Counts money in the month TikTok settled it."],
  ["Stock written off", "The cost of returned units you marked as unsellable."],
  ["Days of cover", "Stock on hand divided by the daily rate of sales over the last fourteen days."],
];

/** @typedef {import("@/lib/api-types").components["schemas"]["ReferenceRule"]} ReferenceRule */

/** @type {Record<string, string>} */
const SET_LABEL = {
  vat: "VAT",
  income_tax: "Income tax and Self Assessment",
  national_insurance: "National Insurance",
  mtd: "Making Tax Digital",
};

/**
 * A short reading of a rule's value, whose shape depends on the rule.
 *
 * @param {unknown} value
 * @returns {string}
 */
function describe(value) {
  if (value && typeof value === "object") {
    const v = /** @type {{ label?: string, amount_minor?: number, currency?: string }} */ (value);
    if (v.label) return v.label;
    if (typeof v.amount_minor === "number") {
      return formatMoney({ amount_minor: v.amount_minor, currency: v.currency ?? "GBP" });
    }
  }
  return String(value ?? "");
}

export default async function GlossaryPage() {
  const result = await api("/rules", { cache: "no-store" });
  const problem = apiProblem(result, { what: "the glossary" });
  if (problem) return problem;

  /** @type {ReferenceRule[]} */
  const rules = result.data.rules ?? [];
  /** @type {Record<string, ReferenceRule[]>} */
  const grouped = {};
  for (const r of rules) (grouped[r.rule_set] ??= []).push(r);

  return (
    <section data-testid="glossary-screen">
      <header className="page-head">
        <h1>Help and glossary</h1>
        <p>What each figure means, and the tax rules MyShopEdge uses with the date each was last checked.</p>
      </header>
      <div className="card" data-testid="glossary-terms">
        <h2>The figures</h2>
        <ul className="rows">
          {TERMS.map(([term, meaning]) => (
            <li key={term}><span>{term}<span className="rows__sub" style={{ display: "block" }}>{meaning}</span></span></li>
          ))}
        </ul>
      </div>
      {rules.length === 0 ? (
        <div className="card">
          <h2>Tax rules</h2>
          <p className="muted">The current HMRC figures will appear here shortly.</p>
        </div>
      ) : (
        <div className="stack">
          {Object.entries(grouped).map(([set, items]) => (
            <div className="card" key={set}>
              <h2>{SET_LABEL[set] ?? set}</h2>
              <ul className="rows">
                {items.map((r) => (
                  <li key={`${r.rule_set}-${r.rule_key}-${r.effective_from}`}>
                    <span>
                      {r.rule_key}
                      <div className="rows__sub">
                        {[describe(r.value),
                          `from ${formatDate(r.effective_from)}`,
                          r.reviewed_at ? `reviewed ${formatDate(r.reviewed_at)}` : null,
                        ].filter(Boolean).join(". ")}
                        {r.source_url && (
                          <> · <a href={r.source_url} target="_blank" rel="noreferrer">source</a></>
                        )}
                      </div>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
