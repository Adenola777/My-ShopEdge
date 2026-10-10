/** Accounts: every account, or the one that holds an email (A34.5). */

import { load } from "@/lib/load";
import { Gate } from "@/components/Gate";
import { AccountActions } from "@/components/AccountActions";
import { day } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Accounts" };

const TONE = /** @type {Record<string, string>} */ ({ active: "chip chip--good", suspended: "chip chip--bad", deleted: "chip" });

/** @param {{ searchParams: Promise<{ email?: string }> }} props */
export default async function Accounts({ searchParams }) {
  const { email } = await searchParams;
  const query = email ? `?email=${encodeURIComponent(email)}` : "";
  const loaded = await load(`/admin/accounts${query}`);
  return (
    <section>
      <h1>Accounts</h1>
      <p className="lede">Find an account by email for a data protection request, or act on one.</p>
      <form className="search" action="/accounts">
        <label htmlFor="email" className="muted">Email</label>
        <input id="email" name="email" type="email" defaultValue={email ?? ""} />
        <button className="btn" type="submit">Find</button>
      </form>
      {loaded.state !== "ok" ? <Gate loaded={loaded} /> : (
        <div className="scroll">
          <table>
            <thead>
              <tr><th>Email</th><th>Status</th><th>Plan</th><th className="num">Shops</th><th>Email notices</th><th>Joined</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {loaded.data.accounts.length === 0 ? (
                <tr><td colSpan={7} className="muted">No account holds that email.</td></tr>
              ) : loaded.data.accounts.map((/** @type {any} */ a) => (
                <tr key={a.account_id}>
                  <td>{a.email}<div className="mono muted">{a.account_id}</div></td>
                  <td>
                    <span className={TONE[a.status] ?? "chip"}>{a.status}</span>
                    {a.deleted_at ? <div className="muted">Closed {day(a.deleted_at)}</div> : null}
                    {a.erased_at ? <div className="muted">Erased {day(a.erased_at)}</div> : null}
                  </td>
                  <td>
                    {a.plan_slug ? `${a.plan_slug}, ${a.plan_status}` : <span className="muted">None</span>}
                    {a.cancel_at_period_end ? <div className="muted">Will not renew</div> : null}
                    {a.trial_end ? <div className="muted">Trial ends {day(a.trial_end)}</div> : null}
                  </td>
                  <td className="num">{a.shop_count}</td>
                  <td>{a.email_notices ? "On" : "Off"}</td>
                  <td>{day(a.created_at)}</td>
                  <td><AccountActions account={a} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
