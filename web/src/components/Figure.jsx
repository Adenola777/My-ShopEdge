/**
 * How a money figure is rendered, everywhere.
 *
 * This component exists for one rule, and the rule is the reason the product is worth
 * anything: **a figure the system cannot compute must never render as a zero.**
 *
 * A4.1 and the products endpoint both take this seriously. `kept` comes back as null with
 * a `kept_reason` when a SKU has no cost, because the seller's profit on that product is
 * unknown, not nil. Rendering it as "£0.00" would be a lie with a currency symbol on it,
 * and it is the kind of lie a seller would act on.
 *
 * So an absent figure renders as the words "Not known" in a muted colour, with the reason
 * attached, and it is announced to a screen reader as the reason.
 */

import { formatMoney } from "@/lib/api";

/**
 * @typedef {import("@/lib/api-types").components["schemas"]["Money"]} Money
 *
 * @param {{
 *   amount: Money | null | undefined,
 *   reason?: string | null,
 *   className?: string,
 *   unsigned?: boolean,
 * }} props
 *
 * `unsigned` shows the amount without its ledger sign, for money whose direction its label
 * already states. Added 8 October 2026 for the payout and the reserve, which the ledger
 * stores negative and a seller read as money taken.
 */
export function Figure({ amount, reason, className = "", unsigned = false }) {
  if (amount == null) {
    const why = reason || "Not known";
    return (
      <span className={`money money--unknown ${className}`} title={why}>
        <span aria-hidden="true">Not known</span>
        <span className="visually-hidden">{why}</span>
      </span>
    );
  }

  const negative = !unsigned && amount.amount_minor < 0;
  const shown = unsigned ? { ...amount, amount_minor: Math.abs(amount.amount_minor) } : amount;
  return (
    <span className={`money ${negative ? "money--neg" : ""} ${className}`}>
      {formatMoney(shown)}
    </span>
  );
}
