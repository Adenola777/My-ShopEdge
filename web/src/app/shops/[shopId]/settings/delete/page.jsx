/**
 * S30 Delete my account, bound to deleteMe. Built 28 September 2026 on A30.1.
 *
 * A3 describes the screen in four steps. Two of them change here. A3's step 2 says every
 * figure, cost and ledger entry is deleted, and A30.1, made later, rules that the ledger
 * stays attached to no person, so this screen says what A30.1 says. A3 asks for the account
 * password as well, and a seller who signs in with Google or GitHub has none, so the
 * contract's typed email address is the confirmation.
 *
 * A3's step 1 offers the data download first, and since 29 September it links to S31.
 * Step 4's email is not sent, because nothing in the service sends email.
 */

import Link from "next/link";
import { fetchShop } from "@/lib/api";
import { apiProblem, NOTHING_CHANGED } from "@/components/ApiProblem";
import { DeleteAccountForm } from "@/components/AccountDeletion";

export const metadata = { title: "Delete my account" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function DeleteAccountPage({ params }) {
  const { shopId } = await params;
  // A read that proves the seller is signed in and the shop is theirs before the page
  // offers anything.
  const result = await fetchShop(shopId, "/alert-settings");
  const problem = apiProblem(result, { what: "your account", note: NOTHING_CHANGED });
  if (problem) return problem;

  return (
    <section data-testid="delete-account-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/settings`}>Settings</Link></p>
        <h1>Delete my account</h1>
        <p>Your account closes now. After thirty days MyShopEdge erases your name and email and deletes your files.</p>
      </header>
      <div className="stack">
        <div className="card">
          <h2>Take your data first</h2>
          <p className="card__why">
            MyShopEdge can build a copy of everything it holds about you. You may want to download
            it before you delete your account.
          </p>
          <p><Link className="btn btn--primary btn--block" href={`/shops/${shopId}/settings/data`} data-testid="take-data">Download my data</Link></p>
        </div>
        <div className="card">
          <h2>What happens</h2>
          <ul className="rows">
            <li><span>Using MyShopEdge</span><strong>Stops now, except to cancel the deletion</strong></li>
            <li><span>Your TikTok Shop connection</span><strong>Ends now. MyShopEdge stops reading your shops but does not ask TikTok to withdraw your approval.</strong></li>
            <li><span>Your plan</span><strong>Stops renewing now, with no refund</strong></li>
            <li><span>Your name and email</span><strong>Erased after 30 days</strong></li>
            <li><span>Your TikTok sign-in details</span><strong>Erased after 30 days</strong></li>
            <li><span>Files you uploaded or exported</span><strong>Deleted after 30 days</strong></li>
            <li><span>Your ledger</span><strong>Kept, with your name and email removed</strong></li>
          </ul>
          <p className="card__why">
            Financial records must be kept after a business stops trading, so MyShopEdge
            keeps your ledger with your name and email removed. MyShopEdge has not yet set when
            that ledger is deleted. For thirty days you can sign in and cancel the deletion.
            Your shops stay disconnected, so you would connect each one again on TikTok.
          </p>
        </div>
        <DeleteAccountForm />
      </div>
    </section>
  );
}
