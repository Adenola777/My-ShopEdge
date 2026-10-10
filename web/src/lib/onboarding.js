/**
 * Where a signed-in seller with a shop belongs, in the onboarding order A14.2 rules:
 *
 *     S17 Start  ->  S1 Connect  ->  S2 First sync  ->  S33 Plan and card  ->  ...  ->  S6 Today
 *
 * Written 28 September 2026 after the sign-in journey was walked in a browser. Until then a
 * seller who connected a shop was sent straight to Today, S2 was reached by nobody, and
 * nothing anywhere linked to S33, so no seller could start a trial.
 *
 * Since 29 September S3, S4, S5, S20 and S35 are built. After the plan, a seller who has
 * neither a cost nor a tax profile is sent to S35 Continue setting up, which names what is
 * left and resumes at the first step. A seller who has either goes to Today, so a seller who
 * chose to skip is not sent back into setup every time.
 *
 * Unverified in one respect: nothing yet moves a shop from `pending` to `connected`, because
 * nothing reads TikTok. Until ingestion is built, a newly connected shop stays on S2.
 *
 * **A36 step 2, 10 October 2026.** The owner's brief now sets the order: connect, import, plan
 * and card, the first reconciliation, then the optional cost choice. Costs and tax no longer
 * come before the figures (A36.1 item 3), so a seller with a plan goes to Overview, which the
 * brief makes the first screen after every sign-in. The first reconciliation is shown once,
 * straight after the trial starts or the import finishes.
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
  return subscriptionStatus === "none" ? "/billing" : `/shops/${shopId}/first-result`;
}

/**
 * The brief's four import steps (section 5), worked out from getSyncStatus's domains. A domain
 * is done when its latest run completed, and under way when it has a run that has not.
 *
 * @param {{ domain: string, status: string }[]} domains
 * @returns {[string, "done" | "now" | "waiting"][]}
 */
export function importSteps(domains) {
  const by = Object.fromEntries(domains.map((d) => [d.domain, d.status]));
  const done = (/** @type {string[]} */ names) => names.every((n) => by[n] === "completed");
  const started = (/** @type {string[]} */ names) => names.some((n) => n in by);
  const orders = ["orders"];
  const money = ["finance", "returns"];
  const all = ["products", "inventory", "orders", "finance", "returns"];
  /** @param {string[]} names */
  const state = (names) => (done(names) ? "done" : started(names) ? "now" : "waiting");
  return [
    ["Connected to your shop", "done"],
    ["Reading orders and sales", state(orders)],
    ["Matching fees, refunds and payouts", state(money)],
    ["Preparing your first summary", done(all) ? "done" : done([...orders, ...money]) ? "now" : "waiting"],
  ];
}
