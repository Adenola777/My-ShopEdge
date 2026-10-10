/**
 * The frame of every shop screen (WFW 1.1): the top bar with the Updated stamp and the bell,
 * one centred column, and the navigation: Overview, Reconcile, Products, Exports and More at
 * the bottom of a phone, and the eight areas as a sidebar on a larger screen (A36.1 item 4). Above each page, on a phone, sits the row of the pages in its area.
 */

import { AppBar } from "@/components/AppBar";
import { SectionNav } from "@/components/SectionNav";
import { ShopNav } from "@/components/ShopNav";

/** @param {{ children: React.ReactNode, params: Promise<{ shopId: string }> }} props */
export default async function ShopLayout({ children, params }) {
  const { shopId } = await params;
  return (
    <div className="shopframe">
      <AppBar shopId={shopId} />
      <main id="main" className="content">
        <SectionNav shopId={shopId} />
        {children}
      </main>
      <ShopNav shopId={shopId} />
    </div>
  );
}
