"use client";

/**
 * The actions on one account (A34.5). Which ones are offered follows the account's status,
 * and the service refuses a wrong one with 409 in any case. Deletion and its cancellation
 * are for a seller's written request only (A30.1).
 */

import Link from "next/link";
import { ActionButton } from "./ActionButton";

/** @param {{ account: import("@/lib/api-types").components["schemas"]["AdminAccount"] }} props */
export function AccountActions({ account }) {
  const id = account.account_id;
  const base = `/admin/accounts/${id}`;
  return (
    <div className="actions">
      {account.status === "active" ? (
        <ActionButton path={`${base}/suspend`} label="Suspend" danger
          confirm={`Suspend ${account.email}? Renewal stops and the seller is emailed.`}
          done="Suspended." />
      ) : null}
      {account.status === "suspended" ? (
        <ActionButton path={`${base}/reactivate`} label="Reactivate"
          confirm={`Reactivate ${account.email}?`} done="Reactivated." />
      ) : null}
      <ActionButton path={`${base}/export`} label="Build export"
        confirm={`Build a data export for ${account.email}?`} done="Export requested."
        onResult={(job) => <Link href={`/accounts/${id}/export/${job.id}`}>Export requested. Open its status</Link>} />
      {account.status === "active" ? (
        <ActionButton path={`${base}/deletion`} label="Close for deletion" danger
          confirm={`Close ${account.email} for deletion on the seller's request? It is erased after thirty days.`}
          done="Closed for deletion." />
      ) : null}
      {account.status === "deleted" && !account.erased_at ? (
        <ActionButton path={`${base}/deletion/cancel`} label="Cancel deletion"
          confirm={`Cancel the deletion of ${account.email}?`} done="Deletion cancelled." />
      ) : null}
    </div>
  );
}
