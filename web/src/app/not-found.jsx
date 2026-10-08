/**
 * The page for an address that does not exist. Added 8 October 2026, because Next's default
 * page carried no way back. It sits under the root layout, which supplies no `<main>`.
 */

import Link from "next/link";

export const metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <main id="main" className="content">
      <section className="state" data-testid="not-found">
        <h1>This page does not exist.</h1>
        <p>The address may be mistyped, or the page may have moved.</p>
        <p><Link className="btn btn--primary" href="/shops">Go to your shops</Link></p>
      </section>
    </main>
  );
}
