/**
 * S4 Upload mapping, drawn to wireframe sheet 03. Built 29 September 2026 on the six cost
 * upload operations: the browser sends the file straight to the signed URL, the seller
 * confirms which column is which, the service matches the rows, and only matched rows are
 * applied. Unmatched and duplicate rows stay visible with their reason, and are never applied.
 */

import Link from "next/link";
import { UploadFlow } from "@/components/SetupForms";

export const metadata = { title: "Upload your costs" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function UploadPage({ params }) {
  const { shopId } = await params;
  return (
    <section data-testid="upload-screen">
      <header className="page-head">
        <p className="crumb"><Link href={`/shops/${shopId}/setup/costs`}>Product costs</Link></p>
        <h1>Check the columns</h1>
        <p>We read your file. Change anything that is wrong before any cost is applied.</p>
      </header>
      <UploadFlow shopId={shopId} />
    </section>
  );
}
