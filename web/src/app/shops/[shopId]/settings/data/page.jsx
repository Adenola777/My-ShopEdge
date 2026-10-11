/**
 * S31 Download my data (A3, ACC-4). Built 29 September 2026 on requestAccountExport and
 * getAccountExport. A3 offers a choice of CSV or JSON. The archive holds both, one file per
 * table in each, so there is nothing to choose. It reuses the export flow of S23, with the
 * same seven-day life.
 */

import Link from "next/link";
import { fetchShop } from "@/lib/api";
import { apiProblem, NOTHING_CHANGED } from "@/components/ApiProblem";
import { DataDownload } from "@/components/SetupForms";

export const metadata = { title: "Data and privacy" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function DataPage({ params }) {
  const { shopId } = await params;
  const check = await fetchShop(shopId, "/alert-settings");
  const problem = apiProblem(check, { what: "your account", note: NOTHING_CHANGED });
  if (problem) return problem;
  return (
    <section data-testid="data-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/settings`}>Settings</Link></p>
        <h1>Data and privacy</h1>
        <p>Your data, how long it is kept, and who to contact.</p>
      </header>
      {/* A36 step 8, the brief's section 18: retention, deletion, and the privacy and support
          contacts. Each period is the Privacy Policy's own, as published on 10 October 2026. */}
      <div className="card" data-testid="data-retention">
        <h2>How long your data is kept</h2>
        <ul className="rows">
          <li><span>Your name and email address</span><span className="muted">While your account is open, and erased thirty days after you delete it.</span></li>
          <li><span>Shop and financial records</span><span className="muted">While your account is open. After it is erased, kept for one year with no name or email, then deleted.</span></li>
          <li><span>Product cost files you upload</span><span className="muted">While your account is open, and erased thirty days after you delete it.</span></li>
        </ul>
        <p className="card__why">
          The <a href="/legal/privacy.html">Privacy Policy</a> sets out every period and your rights.
        </p>
        <p><Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/settings/delete`} data-testid="data-delete">Delete account</Link></p>
        <p className="footnote">You confirm first, and can cancel for 30 days.</p>
      </div>
      <div className="card" data-testid="data-contacts">
        <h2>Contacts</h2>
        <ul className="rows">
          <li><span>Privacy</span><a href="mailto:privacy@inspirecraftglobal.com">privacy@inspirecraftglobal.com</a></li>
          <li><span>Support</span><a href="mailto:support@inspirecraftglobal.com">support@inspirecraftglobal.com</a></li>
        </ul>
      </div>
      <h2>Download my data</h2>
      <div className="card">
        <h2>What the file holds</h2>
        <ul className="rows">
          {["Your account and tax profile", "Your shops", "Orders and order lines", "Your transactions and settlements",
            "Product costs", "Stock and returns", "Exports and notifications", "Your plan and settings",
            "The history of what was read from TikTok"].map((l) => <li key={l}><span>{l}</span></li>)}
        </ul>
        <p className="card__why">CSV and JSON. No buyer details or TikTok sign-in.</p>
      </div>
      <DataDownload />
    </section>
  );
}
