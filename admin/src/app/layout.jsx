/**
 * The admin site's layout (A34.6). A separate Vercel project from the seller app, so a fault
 * in one never ships the other. Built 10 October 2026.
 */

import "@fontsource-variable/plus-jakarta-sans";
import "./globals.css";
import Link from "next/link";
import { StackProvider, StackTheme } from "@stackframe/stack";
import { stackApp } from "@/lib/stack";

export const metadata = {
  title: { default: "MyShopEdge admin", template: "%s | MyShopEdge admin" },
  robots: { index: false, follow: false },
};

const NAV = /** @type {[string, string][]} */ ([
  ["/", "Overview"],
  ["/accounts", "Accounts"],
  ["/shops", "Shops"],
  ["/sync-runs", "Sync runs"],
  ["/webhooks", "Webhooks"],
  ["/emails", "Notice emails"],
  ["/audit", "Audit log"],
]);

/** @param {{ children: React.ReactNode }} props */
export default function RootLayout({ children }) {
  const page = (
    <div className="shell">
      <header className="top">
        <span className="top__name">MyShopEdge admin</span>
        <nav aria-label="Admin">
          {NAV.map(([href, label]) => <Link key={href} href={href}>{label}</Link>)}
          <Link href="/handler/sign-out">Sign out</Link>
        </nav>
      </header>
      <main id="main" className="content">{children}</main>
    </div>
  );
  return (
    <html lang="en-GB">
      <body>
        {stackApp ? (
          <StackProvider app={stackApp}>
            <StackTheme>{page}</StackTheme>
          </StackProvider>
        ) : page}
      </body>
    </html>
  );
}
