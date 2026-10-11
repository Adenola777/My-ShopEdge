/**
 * What an upgrade prompt says, by the feature the plan lacks. The service names the feature
 * and the plan in its `plan_upgrade_required` answer; this file only holds the words.
 *
 * Rewritten 11 October 2026 to the owner's pricing and checkout specification (A38), whose
 * prompts lead with what the seller gets, list what the plan includes, state the monthly price
 * with "Cancel anytime", and offer "Upgrade to <plan>" beside "Maybe later". The two prompts
 * the specification words are used as written: exports (Growth) and gross margin (Starter).
 * The others follow the same form.
 */

/** What each paid plan adds, as its prompt lists it. @type {Record<string, string[]>} */
export const INCLUDES = {
  starter: ["Gross margin by product", "Cost coverage and missing-cost alerts",
    "Return and write-off profit treatment", "Full payout explanations"],
  growth: ["Product profit report", "Full reconciliation details", "Accountant-ready CSV/XLSX",
    "VAT-friendly export structure"],
  pro: ["Up to 10 TikTok Shops", "Unlimited orders", "Scheduled exports and export history",
    "Statements that need review, listed first"],
};

/** @type {Record<string, { title: string, lead?: string }>} */
export const PROMPTS = {
  margin: { title: "See gross margin by product" },
  drilldown: { title: "See the orders behind each figure" },
  payout_detail: { title: "See the full payout explanation", lead: "You can already see each payout's amount and status." },
  exports: { title: "Export product profit", lead: "Your product profit report is ready to build." },
  vat: { title: "Track the VAT threshold", lead: "Growth tracks your rolling 12-month sales against the VAT registration threshold." },
  basis: { title: "Compare sales and cash basis" },
  scheduled_exports: { title: "Schedule your exports" },
  export_history: { title: "Keep your export history" },
  priority_review: { title: "See the statements that need review first" },
  costs: { title: "Add product costs" },
  profit: { title: "See gross profit by product" },
};

/** The service's sentence where profit cannot be shown (`products.NOT_ON_PLAN`). */
export const NOT_ON_PLAN = "Add product costs to see gross profit by product. Gross margin is available on Starter.";

/** @type {Record<string, string>} */
export const PLAN_NAMES = { explorer: "Explorer", starter: "Starter", growth: "Growth", pro: "Pro" };

/**
 * The address that opens the plan's cart on Plans and pricing. `back` is kept for the links
 * written before A38 and is not used by the cart.
 *
 * @param {string} plan
 * @param {string} [_back]
 */
export function changePlanHref(plan, _back) {
  return `/pricing?${new URLSearchParams({ plan }).toString()}`;
}
