/**
 * S31 Download my data (A3, ACC-4). Built 29 September 2026 on requestAccountExport and
 * getAccountExport. A3 offers a choice of CSV or JSON. The archive holds both, one file per
 * table in each, so there is nothing to choose. It reuses the export flow of S23, with the
 * same seven-day life.
 */

import Link from "next/link";
import { fetchShop } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { DataDownload } from "@/components/SetupForms";

export const metadata = { title: "Download my data" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function DataPage({ params }) {
  const { shopId } = await params;
  const check = await fetchShop(shopId, "/alert-settings");
  const problem = apiProblem(check, { what: "your account" });
  if (problem) return problem;
  return (
    <section data-testid="data-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/settings`}>Settings</Link></p>
        <h1>Download my data</h1>
        <p>Everything MyShopEdge holds about your account, in one file.</p>
      </header>
      <div className="card">
        <h2>What the file holds</h2>
        <ul className="rows">
          {["Your account and tax profile", "Your shops", "Orders and order lines", "Your transactions and settlements",
            "Product costs", "Stock and returns", "Exports and notifications"].map((l) => <li key={l}><span>{l}</span></li>)}
        </ul>
        <p className="card__why">Your download holds each part of your records as a spreadsheet file (CSV) and as a data file (JSON). It holds no buyer names or addresses, because MyShopEdge never keeps them. Your TikTok sign-in details are never included.</p>
      </div>
      <DataDownload />
    </section>
  );
}
