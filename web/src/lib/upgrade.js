/**
 * What an upgrade prompt says, by the feature the plan lacks. The service names the feature
 * and the plan in its `plan_upgrade_required` answer; this file only holds the words.
 *
 * The sentences for costs, profit, exports, basis, scheduled exports and the payout review are
 * the owner's, from "MyShopEdge Final Pricing Packaging and Code Command" (10 October 2026),
 * word for word. That document gives none for the transactions behind a figure or for export
 * history, so those two were written here in the same form.
 */

/** @type {Record<string, string>} */
export const PROMPTS = {
  costs:
    "Unlock product profit with Growth. Add costs, see gross profit and margin by product, and identify which products actually make money.",
  profit: "Gross profit needs product costs. Upgrade to Growth to upload costs and see product margin.",
  exports:
    "Export reconciled figures with Growth. Create Excel or CSV month summaries, ledgers and transaction files.",
  basis:
    "Choose how you review activity with Growth. Compare sales-date activity with settlement-date activity.",
  drilldown:
    "See the transactions behind each figure with Growth. Open a product or a line to see the orders and deductions that make it up.",
  scheduled_exports:
    "Automate your reporting with Pro. Schedule weekly or monthly exports and receive a notification when your file is ready.",
  export_history:
    "Keep your export history with Pro. Find the files you made before and build them again.",
  priority_review:
    "Keep routine reconciliation under control with Pro. Prioritise payout exceptions and schedule your regular exports.",
};

/** The sentence Starter shows wherever profit would be, from the same document. */
export const NOT_ON_PLAN = "Add product costs with Growth to see gross profit and margin by product.";

/** @type {Record<string, string>} */
export const PLAN_NAMES = { starter: "Starter", growth: "Growth", pro: "Pro" };

/**
 * The address that changes the plan, returning to `back` afterwards or on "Not now".
 *
 * @param {string} plan
 * @param {string} back
 */
export function changePlanHref(plan, back) {
  return `/billing/change?${new URLSearchParams({ plan, back }).toString()}`;
}
