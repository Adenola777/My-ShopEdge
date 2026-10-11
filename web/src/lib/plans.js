/**
 * How the four plans of A38 (11 October 2026) are worded on screen. The plans, their limits and
 * every price come from the service (`listPlans`); this file holds only words and the shape of
 * the comparison table, from the owner's pricing and checkout specification of that day.
 *
 * Two rules from that specification govern everything below. A feature the product does not
 * have yet is labelled Coming soon and never shown as included (A38.3), and a locked feature
 * is shown with the plan that unlocks it rather than hidden.
 *
 * @typedef {import("./api-types").components["schemas"]} Schemas
 * @typedef {Schemas["Plan"]} Plan
 * @typedef {Schemas["CyclePrice"]} CyclePrice
 * @typedef {"annual" | "annual_monthly" | "monthly"} Cycle
 */

/** @type {Cycle[]} */
export const CYCLES = ["annual", "annual_monthly", "monthly"];

/** @type {Record<Cycle, string>} */
export const CYCLE_LABEL = {
  annual: "Annual prepaid",
  annual_monthly: "Annual, billed monthly",
  monthly: "Monthly",
};

export const VAT_LINE = "Excludes VAT where applicable.";
export const COMMITMENT_LINE =
  "With Annual, billed monthly, all 12 monthly payments must be made in full, even if you cancel.";

/** @type {Record<string, number>} */
export const RANK = { explorer: 0, starter: 1, growth: 2, pro: 3 };

/** A plan's place from Explorer (0) to Pro (3). @param {string | null | undefined} slug */
export function rank(slug) {
  return RANK[slug ?? ""] ?? 0;
}

/**
 * Pounds as the specification writes them: no pence when there are none, so £19 and £15.83.
 *
 * @param {{ amount_minor: number }} money
 */
export function pounds(money) {
  const p = money.amount_minor / 100;
  return `£${Number.isInteger(p) ? p.toLocaleString("en-GB") : p.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Pounds with pence always, for the cart's total. @param {{ amount_minor: number }} money */
export function poundsExact(money) {
  return `£${(money.amount_minor / 100).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** @param {Plan} plan @param {Cycle} cycle @returns {CyclePrice | null} */
export function priceFor(plan, cycle) {
  return plan.prices.find((p) => p.cycle === cycle) ?? null;
}

/**
 * The figure and the line under it on a plan card, for the chosen cycle.
 *
 * @param {Plan} plan
 * @param {Cycle} cycle
 * @returns {{ amount: string, per: string, note: string }}
 */
export function cardPrice(plan, cycle) {
  if (plan.free) return { amount: "Free", per: "", note: "No credit card required" };
  const p = priceFor(plan, cycle);
  if (!p) return { amount: "", per: "", note: "" };
  if (cycle === "annual") {
    return { amount: pounds(p.per_month), per: "/month", note: `${pounds(p.charge)} billed annually · excludes VAT` };
  }
  if (cycle === "annual_monthly") {
    return { amount: pounds(p.charge), per: "/month", note: "12 payments, billed monthly · excludes VAT" };
  }
  return { amount: pounds(p.charge), per: "/month", note: "Billed monthly · excludes VAT" };
}

/**
 * The cart's total and how it is billed.
 *
 * @param {Plan} plan
 * @param {Cycle} cycle
 */
export function cartPrice(plan, cycle) {
  const p = priceFor(plan, cycle);
  if (!p) return { total: "", how: "" };
  if (cycle === "annual") return { total: `${poundsExact(p.charge)} per year`, how: `${pounds(p.per_month)}/month equivalent, billed once a year` };
  if (cycle === "annual_monthly") return { total: `${poundsExact(p.charge)} per month`, how: "12 payments, billed monthly" };
  return { total: `${poundsExact(p.charge)} per month`, how: "Billed monthly. Cancel anytime." };
}

/** The monthly price a prompt quotes, such as "£39/month". @param {Plan | undefined} plan */
export function monthlyLine(plan) {
  const p = plan ? priceFor(plan, "monthly") : null;
  return p ? `${pounds(p.charge)}/month` : "";
}

/**
 * The cart's summary of a plan, from the specification's cart examples.
 *
 * @type {Record<string, string[]>}
 */
export const CART_LINES = {
  starter: ["1 TikTok Shop", "Up to 500 orders/month", "Full product profit and margin",
    "Cost coverage and missing-cost alerts", "Full payout explanations"],
  growth: ["Up to 3 TikTok Shops", "Up to 1,000 orders/month", "Exports included",
    "VAT threshold tracker", "1 accountant seat (coming soon)"],
  pro: ["Up to 10 TikTok Shops", "Unlimited orders", "Everything in Growth",
    "Client workspaces (coming soon)", "Up to 5 accountant/team seats (coming soon)"],
};

/**
 * The upgrade banner above the plans, by the seller's current plan. Pro has none.
 *
 * @type {Record<string, { title: string, body: string, to: string }>}
 */
export const BANNERS = {
  explorer: {
    title: "Need more from MyShopEdge?",
    body: "Upgrade to Growth for £39/month and unlock product profit exports, reconciliation details, VAT tracking and up to 3 TikTok Shops.",
    to: "growth",
  },
  starter: {
    title: "Need exports and more shops?",
    body: "Upgrade to Growth for £39/month and unlock product profit exports, reconciliation details, VAT tracking and up to 3 TikTok Shops.",
    to: "growth",
  },
  growth: {
    title: "Need unlimited orders and client workspaces?",
    body: "Upgrade to Pro for £79/month and manage up to 10 TikTok Shops, client workspaces and accountant access.",
    to: "pro",
  },
};

/**
 * One comparison cell. `yes` is included, `no` is not in this plan, `lock` is available on a
 * larger plan, `soon` is in this plan but not built yet, and a string is the plan's own value.
 * A lock may carry a word, such as Basic or Limited.
 *
 * @typedef {"yes" | "no" | "soon" | { lock: string } | { text: string }} Cell
 * @typedef {{ name: string, cells: [Cell, Cell, Cell, Cell] }} Row
 * @typedef {{ title: string, rows: Row[] }} Section
 */

const Y = /** @type {Cell} */ ("yes");
const N = /** @type {Cell} */ ("no");
const S = /** @type {Cell} */ ("soon");
/** @param {string} [word] @returns {Cell} */
const L = (word = "") => ({ lock: word });
/** @param {string} text @returns {Cell} */
const T = (text) => ({ text });

/** The full comparison, in the specification's sections and order. @type {Section[]} */
export const COMPARISON = [
  {
    title: "Shops and usage",
    rows: [
      { name: "Connected TikTok Shops", cells: [T("1"), T("1"), T("Up to 3"), T("Up to 10")] },
      { name: "Monthly order volume", cells: [T("100"), T("500"), T("1,000"), T("Unlimited")] },
      { name: "Data history", cells: [T("30 days"), T("12 months"), T("24 months"), T("Unlimited")] },
      { name: "Multi-shop consolidated view", cells: [N, N, S, S] },
      { name: "Shop-by-shop comparison", cells: [N, N, S, S] },
    ],
  },
  {
    title: "Costs and profit",
    rows: [
      { name: "Upload product costs", cells: [Y, Y, Y, Y] },
      { name: "Manual cost entry", cells: [Y, Y, Y, Y] },
      { name: "Bulk cost upload", cells: [N, Y, Y, Y] },
      { name: "Gross profit per product", cells: [Y, Y, Y, Y] },
      { name: "Gross margin per product", cells: [L(), Y, Y, Y] },
      { name: "Cost coverage", cells: [L("Basic"), Y, Y, Y] },
      { name: "Missing-cost worklist", cells: [L(), Y, Y, Y] },
      { name: "Return and write-off treatment", cells: [L(), Y, Y, Y] },
    ],
  },
  {
    title: "Reconciliation",
    rows: [
      { name: "Payout list", cells: [Y, Y, Y, Y] },
      { name: "Basic payout status", cells: [Y, Y, Y, Y] },
      { name: "Explain payout drawer", cells: [L("Limited"), Y, Y, Y] },
      { name: "Fee and refund breakdown", cells: [L(), Y, Y, Y] },
      { name: "Statement matching detail", cells: [L(), Y, Y, Y] },
      { name: "Reconciliation status history", cells: [L(), S, S, S] },
    ],
  },
  {
    title: "Exports and reporting",
    rows: [
      { name: "Product profit report export", cells: [L(), L(), Y, Y] },
      { name: "Reconciliation details export", cells: [L(), L(), Y, Y] },
      { name: "Accountant-ready CSV/XLSX", cells: [L(), L(), Y, Y] },
      { name: "VAT threshold tracker", cells: [L(), L(), Y, Y] },
    ],
  },
  {
    title: "Teams and support",
    rows: [
      { name: "Accountant seat", cells: [N, N, T("1, coming soon"), T("Up to 5, coming soon")] },
      { name: "Client workspaces", cells: [N, N, N, S] },
      { name: "Priority support", cells: [N, N, S, S] },
    ],
  },
];

/** The smallest plan whose cell in this row is included, for a lock's label. @param {Row} row */
export function unlockPlan(row) {
  const names = ["Explorer", "Starter", "Growth", "Pro"];
  const i = row.cells.findIndex((c) => c === "yes" || (typeof c === "object" && "text" in c));
  return i >= 0 ? names[i] : "Pro";
}

/** Questions a seller asks before buying. Each answer is a fact about how MyShopEdge works. */
export const FAQ = [
  ["Is Explorer really free?",
    "Yes. Explorer costs nothing and needs no credit card. It covers one TikTok Shop and up to 100 orders a month."],
  ["Can I upload product costs on every plan?",
    "Yes. Every plan, Explorer included, lets you upload a cost file or type costs in, and shows gross profit where costs are added."],
  ["What is the difference between the billing cycles?",
    "Annual prepaid is paid once a year and costs the least. Annual, billed monthly spreads a year over 12 payments, and all 12 are owed even if you cancel. Monthly can be cancelled anytime and runs to the end of the month you have paid for."],
  ["What happens when I upgrade?",
    "The new plan starts immediately, and any unused time on your current plan is prorated."],
  ["What happens when I downgrade?",
    "Your existing data stays where it is. The smaller plan's shop, order and export limits apply, and if you have more shops than it allows you are asked which to disconnect. Nothing is deleted without your confirmation."],
  ["What if I go over my monthly order limit?",
    "We tell you at 80 per cent and again at 100 per cent. Your existing figures stay available, and you can upgrade at any time."],
  ["Do prices include VAT?",
    "Prices exclude VAT where applicable. Inspirecraft Global Ltd is not VAT registered, so no VAT is added today."],
];

/** The trust and security points, each a fact about how payment and data are handled. */
export const TRUST = [
  ["Secure checkout", "Payments are taken by Stripe. MyShopEdge never sees or stores your card number."],
  ["Read-only shop data", "MyShopEdge reads your TikTok Shop data to build your figures. It never changes your shop."],
  ["UK and EU hosting", "Your figures are held in a database in London, and your files in the EU."],
  ["Cancel anytime", "Stop a plan from Settings. Monthly plans run to the end of the month you have paid for."],
];
