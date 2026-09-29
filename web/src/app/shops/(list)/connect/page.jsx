/**
 * Connect another TikTok Shop. Added 29 September 2026 for A31.7, when the owner wanted a
 * second shop on his account. `/shops` sends a seller with one shop straight into it, so
 * without this page nothing offered a second connection. The service stores every shop the
 * authorisation covers, so the seller returns to `/shops` and sees them listed.
 */

import Link from "next/link";
import { ConnectTikTok } from "@/components/ConnectTikTok";

export const metadata = { title: "Connect another shop" };

export default function ConnectAnotherShopPage() {
  return (
    <section>
      <header className="page-head">
        <h1>Connect another TikTok Shop</h1>
        <p>Read-only. MyShopEdge never changes anything in your shop.</p>
      </header>
      <div className="stack">
        <div className="card">
          <p>
            TikTok shows the shops your account can authorise. Every shop you approve is added
            to MyShopEdge, and the shops already connected stay as they are.
          </p>
        </div>
        <ConnectTikTok />
        <p><Link href="/shops">Back to your shops</Link></p>
      </div>
    </section>
  );
}
