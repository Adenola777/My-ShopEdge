"use client";

/**
 * One admin action. Every action changes a seller's account, so each asks once for
 * confirmation before it is sent, says what the service answered, and refreshes the page.
 * The service writes the audit log entry; nothing here records anything.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

/**
 * @param {{ path: string, label: string, confirm: string, done: string, danger?: boolean,
 *           onResult?: (data: any) => import("react").ReactNode }} props
 */
export function ActionButton({ path, label, confirm, done, danger = false, onResult }) {
  const router = useRouter();
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(/** @type {import("react").ReactNode} */ (null));

  async function send() {
    setBusy(true);
    setMessage(null);
    const r = await api(path, { method: "POST" });
    setBusy(false);
    setAsking(false);
    if (r.status === 0) {
      setMessage("The service could not be reached, so nothing was changed.");
      return;
    }
    if (!r.ok) {
      setMessage(r.data?.detail ?? `The service answered ${r.status}, so nothing was changed.`);
      return;
    }
    setMessage(onResult ? onResult(r.data) : done);
    router.refresh();
  }

  return (
    <span className="action">
      {asking ? (
        <>
          <span className="action__ask">{confirm}</span>
          <button type="button" className={danger ? "btn btn--danger" : "btn"} disabled={busy} onClick={send}>
            {busy ? "One moment" : "Yes"}
          </button>
          <button type="button" className="btn btn--quiet" disabled={busy} onClick={() => setAsking(false)}>
            No
          </button>
        </>
      ) : (
        <button type="button" className={danger ? "btn btn--danger" : "btn btn--quiet"} onClick={() => setAsking(true)}>
          {label}
        </button>
      )}
      {message ? <span className="action__said" role="status">{message}</span> : null}
    </span>
  );
}
