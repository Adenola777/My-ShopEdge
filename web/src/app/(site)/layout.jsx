/**
 * Screens outside a shop: Start, sign-in, billing and the TikTok return page. They carry
 * the top bar without the shop's stamp and bell, because there is no shop to be up to date
 * or to notify. A signed in seller also gets Your shops, so billing is never a dead end.
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
