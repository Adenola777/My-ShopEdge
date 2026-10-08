"use client";

/**
 * The progress card on S2 First sync. It polls `getSyncStatus` every four seconds until
 * every domain has completed, so the screen moves on its own.
 *
 * Emergent AI wrote the first version in `Adenola777/MYSHOPEDGE` (commit 3f1bd43). It was
 * rewritten on 28 September 2026 for three faults the review recorded: it showed the raw
 * status code where A8 requires plain words, it used chip styles this stylesheet does not
 * have, and it printed times in the server's zone rather than London's (A29.9).
 *
 * The rows follow wireframe sheet 02: a count found once a domain completes, "Reading" while
 * it runs, "Waiting" before it starts. A domain that has never run is not served (the
 * service describes runs, not intentions), so before the first run the card says so rather
 * than drawing progress that has not happened.
 */

import { useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import { chipClass } from "@/lib/terms";

/** @typedef {import("@/lib/api-types").components["schemas"]["SyncStatus"]} SyncStatus */

/** The contract's five domains, named as sheet 02 and S1 name them. */
/** @type {Record<string, string>} */
const DOMAIN = {
  products: "Products",
  inventory: "Stock",
  orders: "Orders and sales",
  finance: "Payments and fees",
  returns: "Returns and refunds",
};
const ORDER = ["products", "inventory", "orders", "finance", "returns"];

/**
 * Plain words for each run status, and the chip tone that goes with them.
 *
 * @param {{ status: string, records_written?: number }} d
 * @returns {[string, string]}
 */
function describe(d) {
  const n = d.records_written ?? 0;
  switch (d.status) {
    case "completed":
      return [`${n.toLocaleString("en-GB")} found`, "good"];
    case "fetching":
    case "persisting":
    case "processing":
      return ["Reading", "warn"];
    case "scheduled":
      return ["Waiting", "quiet"];
    case "retry_wait":
      return ["Waiting to try again", "warn"];
    case "partial":
      return [`${n.toLocaleString("en-GB")} found so far`, "warn"];
    case "failed":
      return ["Could not be read", "critical"];
    case "needs_reconnect":
      return ["Reconnect needed", "critical"];
    default:
      return ["Waiting", "quiet"];
  }
}

/** @param {{ shopId: string, initial: SyncStatus }} props */
export function SyncProgress({ shopId, initial }) {
  const [data, setData] = useState(initial);
  const domains = [...(data?.domains ?? [])].sort(
    (a, b) => ORDER.indexOf(a.domain) - ORDER.indexOf(b.domain),
  );
  const done = domains.length > 0 && domains.every((d) => d.status === "completed");

  useEffect(() => {
    if (done) return undefined;
    const t = setInterval(async () => {
      const r = await api(`/shops/${encodeURIComponent(shopId)}/sync`, { cache: "no-store" });
      if (r.ok) setData(r.data);
    }, 4000);
    return () => clearInterval(t);
  }, [shopId, done]);

  if (domains.length === 0) {
    return (
      <div className="card" data-testid="sync-waiting">
        <h2>Progress</h2>
        <p className="card__why">
          Nothing has been read from TikTok yet. This card updates on its own when the first
          part of your shop arrives.
        </p>
        <p className="muted">Checked {formatDate(data.as_of, { time: true })}.</p>
      </div>
    );
  }

  return (
    <div className="card" data-testid="sync-progress">
      <h2>Progress</h2>
      <ul className="rows">
        {domains.map((d) => {
          const [words, tone] = describe(d);
          return (
            <li key={d.domain} data-testid={`sync-domain-${d.domain}`}>
              <span>
                {DOMAIN[d.domain] ?? "Other shop data"}
                {d.last_success_at && (
                  <div className="rows__sub">
                    Last read {formatDate(d.last_success_at, { time: true })}
                    {d.stale ? ". This is out of date." : ""}
                  </div>
                )}
              </span>
              <span className={chipClass(tone)}>{words}</span>
            </li>
          );
        })}
      </ul>
      <p className="card__why">
        {done ? "Every part of your shop has been read at least once." : "This card shows each part as it arrives."}
      </p>
      {domains.some((d) => d.status === "failed") && (
        <p className="card__why">A part that could not be read is tried again at the next daily read.</p>
      )}
      {domains.some((d) => d.status === "needs_reconnect") && (
        <p>
          <a className="btn btn--quiet btn--block" href={`/shops/${encodeURIComponent(shopId)}/connection-problem`}>
            Reconnect your shop
          </a>
        </p>
      )}
    </div>
  );
}
