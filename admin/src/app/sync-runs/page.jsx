/** The latest sync runs across every shop (A34.5). */

import { load } from "@/lib/load";
import { Gate } from "@/components/Gate";
import { when } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Sync runs" };

export default async function SyncRuns() {
  const loaded = await load("/admin/sync-runs?limit=200");
  return (
    <section>
      <h1>Sync runs</h1>
      <p className="lede">The latest 200 runs, newest first.</p>
      {loaded.state !== "ok" ? <Gate loaded={loaded} /> : (
        <div className="scroll">
          <table>
            <thead><tr><th>Started</th><th>Shop</th><th>Kind</th><th>Domain</th><th>Status</th><th className="num">Read</th><th className="num">Written</th><th className="num">Failed</th><th>Error</th></tr></thead>
            <tbody>
              {loaded.data.runs.map((/** @type {any} */ r) => (
                <tr key={r.run_id}>
                  <td>{when(r.started_at)}</td>
                  <td>{r.shop_name ?? <span className="mono">{r.shop_id}</span>}</td>
                  <td>{r.kind}</td>
                  <td>{r.domain}</td>
                  <td><span className={r.status === "completed" ? "chip chip--good" : r.status === "failed" ? "chip chip--bad" : "chip"}>{r.status}</span></td>
                  <td className="num">{r.records_read ?? ""}</td>
                  <td className="num">{r.records_written ?? ""}</td>
                  <td className="num">{r.records_failed ?? ""}</td>
                  <td className="muted">{r.error ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
