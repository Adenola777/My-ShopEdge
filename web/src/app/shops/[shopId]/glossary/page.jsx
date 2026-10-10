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

export const metadata = { title: "Glossary and tax rules" };

/** What each figure on the screens means, in the A8 terms. The rules below it come from the service. */
const TERMS = [
  ["Gross sales (GMV)", "Gross sales are what customers paid for your products, before refunds and before anything TikTok takes."],
  ["Seller discounts", "Seller discounts are the discounts you fund yourself, such as your own vouchers."],
  ["Net sales", "Net sales are gross sales less seller discounts and less refunds to customers."],
  ["Total TikTok fees", "Total TikTok fees is the sum of the fees TikTok charges, such as platform commission and affiliate commission. It is always shown under the separate fees that make it up."],
  ["Refunds to customers", "Refunds to customers are the money returned to buyers, in full or in part."],
  ["Net proceeds", "Net proceeds are net sales less every fee and deduction TikTok makes."],
  ["Cost of goods sold", "Cost of goods sold is what the units you sold cost you, at the cost price in force on the day each unit sold."],
  ["Gross profit", "Gross profit is net proceeds less cost of goods sold and the shipping and packaging you pay."],
  ["Gross profit so far", "Gross profit so far is gross profit after returns for the products that have a cost. It is shown while some products still have no cost, with the share of sales value the costs cover."],
  ["Return costs", "Return costs are the return shipping you paid and the cost of returned stock you wrote off."],
  ["Gross profit after returns", "Gross profit after returns is gross profit less return costs. It is before your own running costs and your tax."],
  ["Settlement", "A settlement is a statement from TikTok and the payout it sends to your bank."],
  ["Paid out", "Paid out is what TikTok sent to your bank for a statement, after any reserve it withheld."],
  ["Reserve withheld", "Reserve withheld is money TikTok holds back from a statement for a time before it pays it out."],
  ["Awaiting settlement", "Awaiting settlement is money from your sales that TikTok has not settled yet."],
  ["Sales basis", "Sales basis counts money on the day of the sale."],
  ["Cash basis", "Cash basis counts money in the month TikTok settled it."],
  ["Stock written off", "Stock written off is the cost of returned units you marked as unsellable."],
  ["Days of cover", "Days of cover is stock on hand divided by the daily rate of sales over the last fourteen days."],
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
    const v = /** @type {any} */ (value);
    if (v.label) return v.label;
    if (typeof v.amount_minor === "number") {
      return formatMoney({ amount_minor: v.amount_minor, currency: v.currency ?? "GBP" });
    }
    // Class 4 (reference/class4_nic_2026_27.sql). Until 8 October these two shapes fell
    // through to String(value) and the screen printed "[object Object]".
    if (typeof v.lower_minor === "number" && typeof v.main_rate_bp === "number") {
      return `${pct(v.main_rate_bp)} on profits between ${gbp(v.lower_minor)} and ${gbp(v.upper_minor)}, `
        + `and ${pct(v.upper_rate_bp)} on profits above ${gbp(v.upper_minor)}`;
    }
    // Income Tax bands above the Personal Allowance (reference/income_tax_2026_27.sql).
    if (Array.isArray(v.bands)) {
      return v.bands
        .map((/** @type {{ width_minor: number | null, rate_bp: number }} */ b) =>
          b.width_minor == null ? `${pct(b.rate_bp)} on the rest` : `${pct(b.rate_bp)} on the next ${gbp(b.width_minor)}`)
        .join(", then ");
    }
    return "";
  }
  return String(value ?? "");
}

/** @param {number} minor */
function gbp(minor) {
  return formatMoney({ amount_minor: minor, currency: "GBP" });
}

/** @param {number} bp */
function pct(bp) {
  return `${bp / 100}%`;
}

/** The name a seller reads for each rule, in place of its internal key. */
/** @type {Record<string, string>} */
const RULE_LABEL = {
  income_tax_personal_allowance: "Personal Allowance",
  income_tax_bands: "Income Tax rates above the Personal Allowance (England, Wales and Northern Ireland)",
  class4_nic: "Class 4 National Insurance",
  registration_threshold: "VAT registration threshold",
};

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
        <h1>Glossary and tax rules</h1>
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
          <p className="muted">No tax rules are loaded yet.</p>
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
                      {RULE_LABEL[r.rule_key] ?? r.rule_key}
                      <div className="rows__sub">
                        {[describe(r.value),
                          `It applies from ${formatDate(r.effective_from)}`,
                          r.reviewed_at ? `It was last checked on ${formatDate(r.reviewed_at)}` : null,
                        ].filter(Boolean).join(". ")}.
                        {r.source_url && (
                          <>
                            {" "}
                            <a href={r.source_url} target="_blank" rel="noreferrer">
                              {RULE_LABEL[r.rule_key] ?? "This rule"}{" "}
                              {r.source_url.startsWith("https://www.gov.uk/") ? "on gov.uk" : "at its source"} (opens in a new tab)
                            </a>
                          </>
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
