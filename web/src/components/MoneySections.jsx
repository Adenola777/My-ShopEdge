/**
 * The running calculation of `getMoney` (A8.5), section by section, with each line opening
 * the records behind it in a side panel (A37 phase 2). Moved out of Where the money went on 10 October 2026 (A36 step 5),
 * so that the Overview's "Where the money went" and the page of that name lay out the same
 * calculation the same way. It does no arithmetic: every line and subtotal is the service's.
 */

import { LineLabel } from "@/components/LineLabel";
import { LineDrawer } from "@/components/LineDrawer";
import { Figure } from "@/components/Figure";
import { formatMargin, keptReason } from "@/lib/terms";

/** Lines whose label states their direction, shown without the ledger's sign. */
const UNSIGNED = new Set(["settlement", "reserve_withheld"]);
/** Lines shown in red under the owner's ruling (A36.2 item 3): stock written off. */
const ALERT = new Set(["stock_written_off"]);

/**
 * The records page for a line, over the same period and basis.
 *
 * @param {string} shopId
 * @param {string} basis
 * @param {{ from: string, to: string }} period
 * @param {{ category?: string | null }} line
 */
export function recordsHref(shopId, basis, period, line) {
  return `/shops/${shopId}/records?${new URLSearchParams({
    basis,
    from: period.from,
    to: period.to,
    ...(line.category ? { category: line.category } : {}),
  })}`;
}

/**
 * @param {{
 *   m: import("@/lib/api-types").components["schemas"]["MoneyView"],
 *   shopId: string,
 *   basis: string,
 * }} props
 */
export function MoneySections({ m, shopId, basis }) {
  const period = /** @type {{ from: string, to: string }} */ (m.period);
  return (
    <div className="stack">
      {m.sections.map((s) => (
        <div className="card" key={s.key}>
          <h2>{s.label}</h2>
          <ul className="rows">
            {s.lines.map((l, i) => (
              <li key={`${l.category}-${l.tiktok_fee_type ?? i}`}>
                {/* A37 phase 2: the line opens its records in a side panel, and stays a link to
                    the Transactions page for a new tab or a browser without JavaScript. */}
                <LineDrawer
                  href={recordsHref(shopId, basis, period, l)}
                  path={recordsHref(shopId, basis, period, l)}
                  title={l.label}
                  label={<LineLabel line={l} />}
                />
                <Figure amount={l.amount} unsigned={UNSIGNED.has(l.category ?? "")} alert={ALERT.has(l.category ?? "")} />
              </li>
            ))}
            {s.key !== "payout" && (
              <li className="rows__total">
                <span>{s.subtotal_label ?? "Subtotal"}</span>
                <Figure amount={s.subtotal} reason={s.key === "return_costs" ? keptReason(m.kept_reason) : null} />
              </li>
            )}
            {s.key === "return_costs" && formatMargin(m.totals?.gross_margin_after_returns) && (
              <li data-testid="money-margin">
                <span>Gross margin after returns, as a share of net sales</span>
                <strong className="money">{formatMargin(m.totals.gross_margin_after_returns)}</strong>
              </li>
            )}
          </ul>
        </div>
      ))}
    </div>
  );
}
