/**
 * Overview: the business figures (A34.5). The revenue figure is each paying plan's list
 * price, not money taken, and the page says so in the service's own words.
 */

import { load } from "@/lib/load";
import { Gate } from "@/components/Gate";
import { pounds } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Overview" };

const PLAN = /** @type {Record<string, string>} */ ({ starter: "Starter", growth: "Growth", pro: "Pro" });

export default async function Overview() {
  const loaded = await load("/admin/figures");
  if (loaded.state !== "ok") return <><h1>Overview</h1><Gate loaded={loaded} /></>;
  /** @type {import("@/lib/api-types").components["schemas"]["AdminFigures"]} */
  const f = loaded.data;
  const trialing = f.plans.reduce((n, p) => n + p.trialing, 0);
  const paying = f.plans.reduce((n, p) => n + p.paying, 0);
  const pastDue = f.plans.reduce((n, p) => n + p.past_due, 0);
  return (
    <section>
      <h1>Overview</h1>
      <p className="lede">Accounts and plans across every seller.</p>
      <div className="tiles">
        <div className="tile"><div className="tile__label">Accounts</div><div className="tile__value">{f.accounts}</div></div>
        <div className="tile"><div className="tile__label">Active accounts</div><div className="tile__value">{f.accounts_active}</div></div>
        <div className="tile"><div className="tile__label">On trial</div><div className="tile__value">{trialing}</div></div>
        <div className="tile"><div className="tile__label">Paying</div><div className="tile__value">{paying}</div></div>
        <div className="tile"><div className="tile__label">Payment failed</div><div className="tile__value">{pastDue}</div></div>
        <div className="tile"><div className="tile__label">Monthly list revenue</div><div className="tile__value">{pounds(f.list_revenue_minor)}</div></div>
      </div>
      <p className="muted">{f.note}</p>

      <h2>By plan</h2>
      <div className="scroll">
        <table>
          <thead><tr><th>Plan</th><th className="num">On trial</th><th className="num">Paying</th><th className="num">Payment failed</th><th className="num">Monthly list revenue</th></tr></thead>
          <tbody>
            {f.plans.map((p) => (
              <tr key={p.plan_slug}>
                <td>{PLAN[p.plan_slug] ?? p.plan_slug}</td>
                <td className="num">{p.trialing}</td>
                <td className="num">{p.paying}</td>
                <td className="num">{p.past_due}</td>
                <td className="num">{pounds(p.list_revenue_minor)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Sign-ups by month</h2>
      <div className="scroll">
        <table>
          <thead><tr><th>Month</th><th className="num">Sign-ups</th></tr></thead>
          <tbody>
            {f.signups_by_month.map((m) => <tr key={m.month}><td>{m.month}</td><td className="num">{m.signups}</td></tr>)}
          </tbody>
        </table>
      </div>
    </section>
  );
}
