/**
 * Locked features, A38 (11 October 2026). The owner's specification asks that a locked feature
 * stay visible with the plan that unlocks it, in neutral grey and never red, with one upgrade
 * action, so a seller sees the shape of what they would get rather than a blank. Prices are the
 * service's.
 */

import Link from "next/link";
import { fetchPlans } from "@/lib/api";
import { monthlyLine } from "@/lib/plans";
import { PLAN_NAMES, changePlanHref } from "@/lib/upgrade";
import { LockIcon } from "./Pricing";

/** "Upgrade to Growth for £39/month", from the service's price. @param {string} plan */
async function upgradeLabel(plan) {
  const payload = await fetchPlans();
  const line = monthlyLine(payload?.plans.find((p) => p.slug === plan));
  const name = PLAN_NAMES[plan] ?? plan;
  return line ? `Upgrade to ${name} for ${line}` : `Upgrade to ${name}`;
}

/**
 * A block of features a larger plan adds: "Available on Starter", the list, one action.
 *
 * @param {{ plan: string, items: string[], title?: string, lead?: string, testId?: string }} props
 */
export async function LockedBlock({ plan, items, title, lead, testId = "locked" }) {
  const name = PLAN_NAMES[plan] ?? plan;
  return (
    <section className="locked" data-testid={testId} aria-label={`Available on ${name}`}>
      <p className="locked__head"><LockIcon /> {title ?? `Available on ${name}`}</p>
      {lead && <p className="rows__sub">{lead}</p>}
      <ul className="locked__list">
        {items.map((i) => <li key={i}>{i}</li>)}
      </ul>
      <Link className="btn btn--primary btn--small" href={changePlanHref(plan)}>{await upgradeLabel(plan)}</Link>
    </section>
  );
}

/** The four exports Growth adds, shown in full and locked (the specification's example). */
const EXPORT_ROWS = [
  ["Product profit report", "Sales, deductions, costs, gross profit and margin by product."],
  ["Reconciliation details", "Payouts, linked statements, fees, refunds and differences."],
  ["Accountant-ready export", "A structured CSV/XLSX for bookkeeping and VAT preparation."],
  ["VAT threshold report", "Rolling 12-month sales and threshold tracking."],
];

/** Exports for a plan without them: the structure, each row locked to Growth. */
export async function LockedExports() {
  return (
    <section data-testid="exports-locked">
      <header className="page-head">
        <h1>Exports</h1>
        <p>Choose what you want to download.</p>
      </header>
      <div className="card">
        {EXPORT_ROWS.map(([name, what]) => (
          <div key={name} className="locked-row">
            <span>
              <span className="locked-row__name">{name}</span>
              <span className="locked-row__what">{what}</span>
            </span>
            <span className="locked-row__plan"><LockIcon /> Growth</span>
          </div>
        ))}
      </div>
      <div className="overview__more">
        <p>Exports are available on Growth. You can already understand your profit. Growth lets you export product profit, reconciliation details and accountant-ready files, with VAT tracking, up to 3 TikTok Shops and one accountant seat (coming soon).</p>
        <Link className="btn btn--primary" href={changePlanHref("growth")} data-testid="exports-upgrade">{await upgradeLabel("growth")}</Link>
      </div>
    </section>
  );
}
