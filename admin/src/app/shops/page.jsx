/**
 * Shops: every shop, its connection and its last sync (A34.5). Statements are shown as counts
 * only, never amounts (A34.8, ruling 4).
 */

import { load } from "@/lib/load";
import { Gate } from "@/components/Gate";
import { ActionButton } from "@/components/ActionButton";
import { when } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Shops" };

export default async function Shops() {
  const loaded = await load("/admin/shops");
  return (
    <section>
      <h1>Shops</h1>
      <p className="lede">Each shop's connection, last sync and statements, across every account.</p>
      {loaded.state !== "ok" ? <Gate loaded={loaded} /> : (
        <div className="scroll">
          <table>
            <thead>
              <tr><th>Shop</th><th>Account</th><th>Connection</th><th>Last sync</th><th>Token</th><th className="num">Statements</th><th className="num">Not reconciled</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {loaded.data.shops.map((/** @type {any} */ s) => (
                <tr key={s.shop_id}>
                  <td>{s.shop_name ?? <span className="muted">No name</span>}<div className="mono muted">{s.tiktok_shop_code ?? ""} {s.region} {s.seller_type ?? ""}</div></td>
                  <td>{s.account_email}</td>
                  <td><span className={s.connection_status === "connected" ? "chip chip--good" : "chip chip--bad"}>{s.connection_status}</span>
                    {s.revoked_at ? <div className="muted">Revoked {when(s.revoked_at)}</div> : null}</td>
                  <td>{when(s.last_synced_at) || <span className="muted">Never</span>}</td>
                  <td>
                    {s.access_expires_at ? <div>Expires {when(s.access_expires_at)}</div> : null}
                    {s.refresh_succeeded_at ? <div className="muted">Refreshed {when(s.refresh_succeeded_at)}</div> : null}
                    {s.refresh_failure_code ? <div className="chip chip--bad">Refresh failed {s.refresh_failure_code}</div> : null}
                    {s.refresh_failure_reason ? <div className="muted">{s.refresh_failure_reason}</div> : null}
                  </td>
                  <td className="num">{s.statements}</td>
                  <td className="num">{s.statements_unexplained}</td>
                  <td>
                    <ActionButton path={`/admin/shops/${s.shop_id}/sync`} label="Sync now"
                      confirm="Read this shop from TikTok now?" done="Sync started. It runs in the background." />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
