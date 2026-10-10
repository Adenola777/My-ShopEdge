/**
 * The words the screens use, from the A8 terminology standard.
 *
 * These are copy, not rules. Every figure and every state they describe is computed by the
 * service (A29.1), and this file only names what the service returned. TC-CLR-06 forbids
 * the withdrawn labels "Their cut", "You keep", "Left after TikTok", "Contribution" and
 * "Return Loss" on any screen, so none of them appears here.
 */

import { NOT_ON_PLAN } from "./upgrade";
import { formatMoney } from "./api";

/** The statement CLR-5 requires wherever gross profit after returns is shown. */
export const BEFORE_OVERHEADS = "This is before your own running costs and your tax.";

/**
 * Gross margin after returns as words, from the service's fraction (0.4752 reads "47.5%").
 * The service owns the rule (A29) and sends null when the margin is not known, so this only
 * formats. One decimal place is enough to compare products. Added 10 October 2026.
 * @param {number | null | undefined} m
 */
export function formatMargin(m) {
  if (m === null || m === undefined) return null;
  return `${(m * 100).toLocaleString("en-GB", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

/**
 * The brief's coverage sentence (section 9, A36), from the service's `coverage`. Nothing when
 * every product sold has a cost, or when the plan holds no product costs. The share is shown to
 * one decimal place at most, so 99.6 per cent never reads as 100.
 *
 * @param {{ share_of_sales?: number | null, products_missing: number, sales_missing: { amount_minor: number, currency?: string } } | null | undefined} c
 */
export function coverageSentence(c) {
  if (!c || c.products_missing === 0) return null;
  const share = c.share_of_sales == null ? null
    : `${(Math.floor(c.share_of_sales * 1000) / 10).toLocaleString("en-GB", { maximumFractionDigits: 1 })}%`;
  const products = `${c.products_missing} ${c.products_missing === 1 ? "product" : "products"}`;
  return `${share ? `Based on product costs for ${share} of sales value. ` : ""}Costs are still missing for ${products} affecting ${formatMoney(/** @type {any} */ (c.sales_missing))} of sales.`;
}

/** @type {Record<string, string>} */
export const HERO_LABEL = {
  gross_profit_after_returns: "Gross profit after returns",
  net_proceeds: "Net proceeds",
};

/*
 * Chip tones. A7.10 keeps red, amber and green for the three payment statuses and nothing
 * else, "so that red on this product always means money that has not arrived". Every other
 * state here is navy (`critical`, `strong`) or neutral (`quiet`), and the word carries the
 * meaning. Until 24 September these used the payment colours.
 */

/** @type {Record<string, [string, string]>} label and chip tone */
export const CONFIDENCE = {
  confirmed: ["Confirmed", "quiet"],
  estimated: ["Estimated", "strong"],
  incomplete: ["Incomplete", "strong"],
};

/**
 * What each confidence chip means, for its title. The rule is the service's
 * (service/app/money_view.py): incomplete when a product sold has no cost price, estimated
 * on the sales basis when some sales are not yet settled, and confirmed otherwise.
 *
 * @type {Record<string, string>}
 */
export const CONFIDENCE_MEANING = {
  estimated: "Estimated means TikTok has not yet settled some of these sales.",
  incomplete: "Incomplete means not every product sold has a cost price yet.",
};

/** @type {Record<string, [string, string]>} */
export const FRESHNESS = {
  fresh: ["Up to date", "quiet"],
  getting_old: ["Not current", "strong"],
  stale: ["Out of date", "critical"],
};

/** @type {Record<string, string>} */
export const AWAITING = {
  waiting_delivery: "Waiting for delivery",
  waiting_return_refund: "Waiting on a return or refund",
  delivered_awaiting_settlement: "Delivered, awaiting settlement",
};

/** @type {Record<string, [string, string]>} */
export const STOCK_STATE = {
  out: ["Out of stock", "critical"],
  low: ["Low", "strong"],
  coming_back: ["Returns in transit", "quiet"],
  healthy: ["Healthy", "quiet"],
};

/** A18.8 names movements in plain English rather than by their codes. */
/** @type {Record<string, string>} */
export const MOVEMENT = {
  sale_reserved: "Sold, not yet dispatched",
  posted: "Dispatched",
  cancelled: "Order cancelled, units back in stock",
  return_resellable: "Returned, back in stock",
  write_off: "Stock written off",
  manual_adjustment: "Adjusted by you",
  adjustment_absorbed: "TikTok's count rose, so MyShopEdge reduced your adjustment",
};

/** @type {Record<string, string>} */
export const DISCREPANCY_KIND = {
  product_code: "Product code differs",
  order_reference: "Order reference differs",
  transaction_reference: "Transaction reference differs",
  amount: "Amount differs",
  return_unmatched: "Return not matched to an order",
  duplicate: "Recorded twice",
  unmapped_fee: "Fee MyShopEdge does not recognise",
};

/** @type {Record<string, string>} */
export const RESOLUTION = {
  accepted_tiktok: "TikTok's value accepted",
  corrected_seller: "Your record corrected",
  explained: "Marked as explained",
};

/** Where a record came from, from the ledger's `source` column. */
/** @type {Record<string, string>} */
export const RECORD_SOURCE = {
  tiktok: "From TikTok",
  seller: "Entered by you",
  system: "Worked out by MyShopEdge",
};

/** @type {Record<string, string>} */
export const SEVERITY_TONE = { critical: "critical", warning: "strong", info: "quiet" };

/** @param {string} tone */
export function chipClass(tone) {
  return `chip chip--${tone}`;
}

/**
 * Why gross profit after returns is not shown. The contract serves a code on Money and
 * Today, `incomplete_costs`, `no_sales` or, on Starter since 10 October 2026, `not_on_plan`,
 * and the product ranking serves a sentence, so a value that is not a known code is shown as
 * it came.
 *
 * @param {string | null | undefined} reason
 */
export function keptReason(reason) {
  if (!reason) return null;
  return (
    {
      incomplete_costs: "Not every product has a cost price yet, so profit cannot be worked out.",
      no_sales: "Nothing sold in this period.",
      not_on_plan: NOT_ON_PLAN,
    }[reason] ?? reason
  );
}
