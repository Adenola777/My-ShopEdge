/** The audit log: every admin action, newest first (A34.5). It cannot be edited. */

import { load } from "@/lib/load";
import { Gate } from "@/components/Gate";
import { when } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Audit log" };

export default async function Audit() {
  const loaded = await load("/admin/audit?limit=200");
  return (
    <section>
      <h1>Audit log</h1>
      <p className="lede">Every admin action writes one entry, and no entry can be changed or removed.</p>
      {loaded.state !== "ok" ? <Gate loaded={loaded} /> : loaded.data.entries.length === 0 ? (
        <p className="note">No admin action has been taken.</p>
      ) : (
        <div className="scroll">
          <table>
            <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Account</th><th>On</th></tr></thead>
            <tbody>
              {loaded.data.entries.map((/** @type {any} */ e) => (
                <tr key={e.audit_id}>
                  <td>{when(e.occurred_at)}</td>
                  <td>{e.actor}</td>
                  <td>{e.action}</td>
                  <td className="mono">{e.account_id ?? ""}</td>
                  <td>{e.entity_type ?? ""} <span className="mono muted">{e.entity_id ?? ""}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
