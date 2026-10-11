/**
 * Screens outside a shop: Start, sign-in, billing and the TikTok return page. They carry
 * the top bar without the shop's stamp and bell, because there is no shop to be up to date
 * or to notify. A signed in seller has the account menu, and a visitor who is not signed in
 * has the website's main links with Log in and Start free (11 October 2026), so no screen is a
 * dead end.
 */

import { AppBar } from "@/components/AppBar";
import { currentUser } from "@/lib/stack";

/** @param {{ children: React.ReactNode }} props */
export default async function SiteLayout({ children }) {
  const signedIn = Boolean(await currentUser());
  return (
    <>
      <AppBar shopsLink={signedIn} />
      <main id="main" className="content">{children}</main>
    </>
  );
}
