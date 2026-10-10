/** Notice emails: how many are in each state, and the ones not yet sent (A34.5). */

import { load } from "@/lib/load";
import { Gate } from "@/components/Gate";
import { ActionButton } from "@/components/ActionButton";
import { when } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Notice emails" };

const STATES = /** @type {[string, string][]} */ ([
  ["pending", "Waiting to be sent"],
  ["sent", "Sent"],
  ["not_emailed", "Not emailed by rule"],
  ["failed", "Failed"],
  ["predates_email", "Written before email existed"],
]);

export default async function Emails() {
  const loaded = await load("/admin/notice-emails?limit=200");
  return (
    <section>
      <h1>Notice emails</h1>
      <p className="lede">Emails sent through Resend for the notices NTF-2, A16.3, A5.7 and A34 name.</p>
      {loaded.state !== "ok" ? <Gate loaded={loaded} /> : (
        <>
          <div className="tiles">
            {STATES.map(([key, label]) => (
              <div className="tile" key={key}><div className="tile__label">{label}</div><div className="tile__value">{loaded.data.counts[key] ?? 0}</div></div>
            ))}
          </div>
          <h2>Waiting or failed</h2>
          {loaded.data.problems.length === 0 ? <p className="note">No email is waiting or has failed.</p> : (
            <div className="scroll">
              <table>
                <thead><tr><th>Written</th><th>Account</th><th>Notice</th><th>State</th><th className="num">Tries</th><th>Resend's answer</th><th>Actions</th></tr></thead>
                <tbody>
                  {loaded.data.problems.map((/** @type {any} */ p) => (
                    <tr key={p.notification_id}>
                      <td>{when(p.created_at)}</td>
                      <td>{p.account_email}</td>
                      <td>{p.type}</td>
                      <td><span className={p.email_status === "failed" ? "chip chip--bad" : "chip"}>{p.email_status}</span></td>
                      <td className="num">{p.email_attempts}</td>
                      <td className="muted">{p.email_note ?? ""}</td>
                      <td>{p.email_status === "failed" ? (
                        <ActionButton path={`/admin/notifications/${p.notification_id}/retry-email`} label="Try again"
                          confirm="Send this email again?" done="Put back to send." />
                      ) : null}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
