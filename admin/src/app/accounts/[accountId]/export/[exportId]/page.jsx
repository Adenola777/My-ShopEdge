/** One account export's status, and its signed link once ready (A34.5). */

import Link from "next/link";
import { load } from "@/lib/load";
import { Gate } from "@/components/Gate";
import { when } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Account export" };

/** @param {{ params: Promise<{ accountId: string, exportId: string }> }} props */
export default async function AccountExport({ params }) {
  const { accountId, exportId } = await params;
  const loaded = await load(`/admin/accounts/${accountId}/export/${exportId}`);
  return (
    <section>
      <h1>Account export</h1>
      <p><Link href="/accounts">Back to accounts</Link></p>
      {loaded.state !== "ok" ? <Gate loaded={loaded} /> : (
        <table>
          <tbody>
            <tr><th>Status</th><td>{loaded.data.status}</td></tr>
            <tr><th>Requested</th><td>{when(loaded.data.requested_at)}</td></tr>
            {loaded.data.ready_at ? <tr><th>Ready</th><td>{when(loaded.data.ready_at)}</td></tr> : null}
            {loaded.data.expires_at ? <tr><th>Expires</th><td>{when(loaded.data.expires_at)}</td></tr> : null}
            {loaded.data.download_url ? (
              <tr><th>File</th><td><a href={loaded.data.download_url}>Download</a> <span className="muted">The link expires.</span></td></tr>
            ) : null}
          </tbody>
        </table>
      )}
    </section>
  );
}
