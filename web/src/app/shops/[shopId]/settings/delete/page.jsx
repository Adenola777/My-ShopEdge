/**
 * S30 Delete my account, bound to deleteMe. Built 28 September 2026 on A30.1.
 *
 * A3 describes the screen in four steps. Two of them change here. A3's step 2 says every
 * figure, cost and ledger entry is deleted, and A30.1, made later, rules that the ledger
 * stays attached to no person, so this screen says what A30.1 says. A3 asks for the account
 * password as well, and a seller who signs in with Google or GitHub has none, so the
 * contract's typed email address is the confirmation.
 *
 * A3's step 1 offers the data download first. S31 and requestAccountExport are not built,
 * so the screen says the download is not built rather than offering nothing silently.
 * An earlier draft pointed the seller to exports on each screen, and createExport is not
 * built either, so that sentence was removed before it was committed. Step 4's email is not sent, because nothing in the service sends email.
 */

import Link from "next/link";
import { fetchShop } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { DeleteAccountForm } from "@/components/AccountDeletion";

export const metadata = { title: "Delete my account" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function DeleteAccountPage({ params }) {
  const { shopId } = await params;
  // A read that proves the seller is signed in and the shop is theirs before the page
  // offers anything.
  const result = await fetchShop(shopId, "/alert-settings");
  const problem = apiProblem(result, { what: "your account" });
  if (problem) return problem;

  return (
    <section data-testid="delete-account-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/settings`}>Settings</Link></p>
        <h1>Delete my account</h1>
        <p>Your account closes now and is erased after thirty days.</p>
      </header>
      <div className="stack">
        <div className="card">
          <h2>Take your data first</h2>
          <p className="card__why">
            A download of your data is not built yet, so MyShopEdge cannot give you a copy
            before the account closes.
          </p>
        </div>
        <div className="card">
          <h2>What happens</h2>
          <ul className="rows">
            <li><span>Signing in</span><strong>Stops now</strong></li>
            <li><span>Your TikTok Shop connection</span><strong>Ends now</strong></li>
            <li><span>Your name and email</span><strong>Erased after 30 days</strong></li>
            <li><span>Stored TikTok tokens</span><strong>Erased after 30 days</strong></li>
            <li><span>Files you uploaded or exported</span><strong>Deleted after 30 days</strong></li>
            <li><span>Your ledger</span><strong>Kept, attached to no person</strong></li>
          </ul>
          <p className="card__why">
            Financial records must be kept for a period after a business stops trading, so
            the ledger stays without your name or email on it. For thirty days you can sign
            in and keep your account.
          </p>
        </div>
        <DeleteAccountForm />
      </div>
    </section>
  );
}
