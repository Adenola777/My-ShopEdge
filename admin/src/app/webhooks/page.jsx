/** The latest TikTok webhook events and how each was processed (A34.5). No payload is shown. */

import { load } from "@/lib/load";
import { Gate } from "@/components/Gate";
import { when } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Webhooks" };

export default async function Webhooks() {
  const loaded = await load("/admin/webhook-events?limit=200");
  return (
    <section>
      <h1>TikTok webhooks</h1>
      <p className="lede">The latest 200 events TikTok delivered, newest first.</p>
      {loaded.state !== "ok" ? <Gate loaded={loaded} /> : loaded.data.events.length === 0 ? (
        <p className="note">No TikTok event has reached the service.</p>
      ) : (
        <div className="scroll">
          <table>
            <thead><tr><th>Received</th><th>Event</th><th>TikTok shop</th><th>Outcome</th><th>Note</th></tr></thead>
            <tbody>
              {loaded.data.events.map((/** @type {any} */ e) => (
                <tr key={e.event_id}>
                  <td>{when(e.received_at)}</td>
                  <td>{e.event_type ?? ""}</td>
                  <td className="mono">{e.tiktok_shop_id ?? ""}</td>
                  <td>{e.process_status ?? <span className="muted">Not processed</span>}</td>
                  <td className="muted">{e.process_note ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
