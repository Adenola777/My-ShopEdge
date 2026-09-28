/**
 * Where a signed-in seller with a shop belongs, in the onboarding order A14.2 rules:
 *
 *     S17 Start  ->  S1 Connect  ->  S2 First sync  ->  S33 Plan and card  ->  ...  ->  S6 Today
 *
 * Written 28 September 2026 after the sign-in journey was walked in a browser. Until then a
 * seller who connected a shop was sent straight to Today, S2 was reached by nobody, and
 * nothing anywhere linked to S33, so no seller could start a trial.
 *
 * S3, S4, S5 and S20 are not built, so after the plan the order goes to Today. A14 also
 * describes S35 Continue setting up for a seller who comes back part way; until it is built,
 * this function is what resumes them at the right step.
 *
 * Unverified in one respect: nothing yet moves a shop from `pending` to `connected`, because
 * nothing reads TikTok. Until ingestion is built, a newly connected shop stays on S2.
 */

/** @typedef {import("./api-types").components["schemas"]["Shop"]} Shop */

/**
 * @param {Shop} shop
 * @param {string | null} subscriptionStatus  From getSubscription, or null when unknown.
 * @returns {string} The path to send the seller to.
 */
export function nextStep(shop, subscriptionStatus) {
  const base = `/shops/${shop.id}`;
  if (shop.connection_status === "needs_reconnect" || shop.connection_status === "disconnected") {
    return `${base}/connection-problem`;
  }
  if (shop.connection_status === "pending") return `${base}/sync`;
  // An unknown subscription is not treated as none: a failed request must not push a
  // paying seller back to the plans.
  if (subscriptionStatus === "none") return "/billing";
  return `${base}/today`;
}

/**
 * Where S2's button leads: the plan if none has been chosen, otherwise the shop.
 *
 * @param {string} shopId
 * @param {string | null} subscriptionStatus
 */
export function afterSync(shopId, subscriptionStatus) {
  return subscriptionStatus === "none" ? "/billing" : `/shops/${shopId}/products`;
}
