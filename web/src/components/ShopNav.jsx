"use client";

/**
 * The shop's tabs (WFW 1.1): at the bottom on a phone, a left rail on a larger screen
 * (WFW 7). The wireframes carry five: Today, Stock, Products, Money and Tax. Tax was left
 * out until 28 September because its screen did not exist. It exists now, as a threshold
 * monitor and a list of dates rather than a VAT filing feature (A29.8), so the fifth tab is
 * back. Settings is not a tab: it is reached from the top bar, as sheet 09 draws it, and
 * from More.
 *
 * The icons are simple line drawings, so each tab is named by its word and the icon only
 * helps the eye find it.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

/** @type {Record<string, React.ReactElement>} */
const ICON = {
  today: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3.5" y="4.5" width="17" height="16" rx="2.5" />
      <path d="M3.5 9.5h17M8 2.5v4M16 2.5v4" />
    </svg>
  ),
  stock: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3.5 7.5 12 3l8.5 4.5v9L12 21l-8.5-4.5z" />
      <path d="M3.5 7.5 12 12l8.5-4.5M12 12v9" />
    </svg>
  ),
  products: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 12.5V4.5A1.5 1.5 0 0 1 4.5 3h8l8.5 8.5-9.5 9.5z" />
      <circle cx="8" cy="8" r="1.6" />
    </svg>
  ),
  money: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M16.5 6.5a4 4 0 0 0-7 2.5v9.5M7 18.5h10M7 13h7" />
    </svg>
  ),
  more: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  ),
  tax: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6" />
    </svg>
  ),
};

/** @type {[string, string][]} */
const TABS = [
  ["today", "Today"],
  ["stock", "Stock"],
  ["products", "Products"],
  ["money", "Money"],
  ["tax", "Tax"],
];

/**
 * Everything else a seller needs, each with one line saying what it is for. On a phone
 * these sit behind More, because five tabs is what fits across a phone. On a larger
 * screen they are listed in the rail under the tabs. Added 30 September 2026 at the
 * owner's request, because nothing but the address bar reached these screens.
 *
 * @type {[string, string, string][]}
 */
const MORE = [
  ["setup/costs", "Product costs", "Upload a cost file or type costs in"],
  ["returns", "Returns", "Check what came back and whether it can be resold"],
  ["records", "Records", "Every transaction behind the figures"],
  ["notifications", "Notifications", "What needs your attention"],
  ["settings", "Settings", "Your shop connection, alerts and data"],
  ["glossary", "Help and glossary", "What each figure and word means"],
];

/** @param {{ shopId: string }} props */
export function ShopNav({ shopId }) {
  const path = usePathname() ?? "";
  const base = `/shops/${shopId}`;
  const [open, setOpen] = useState(false);
  // A new screen closes the sheet, so it never covers the page it opened.
  useEffect(() => setOpen(false), [path]);
  const moreCurrent = MORE.some(([slug]) => path === `${base}/${slug}` || path.startsWith(`${base}/${slug}/`));
  return (
    <nav className={`tabs${open ? " tabs--open" : ""}`} aria-label="Your shop">
      {TABS.map(([slug, label]) => {
        const href = `${base}/${slug}`;
        const current = path === href || path.startsWith(`${href}/`)
          // Other-channel sales exist only to complete the VAT monitor's turnover.
          || (slug === "tax" && path.startsWith(`${base}/other-sales`))
          || (slug === "today" && path.startsWith(`${base}/discrepancies`));
        return (
          <Link key={slug} className="tabs__tab" href={href} aria-current={current ? "page" : undefined}>
            {ICON[slug]}
            <span>{label}</span>
          </Link>
        );
      })}
      <button
        type="button"
        className="tabs__tab tabs__more"
        aria-expanded={open}
        aria-controls="shop-more"
        aria-current={moreCurrent && !open ? "page" : undefined}
        onClick={() => setOpen((o) => !o)}
      >
        {ICON.more}
        <span>More</span>
      </button>
      <div className="tabs__sheet" id="shop-more">
        <p className="tabs__heading">More</p>
        <ul>
          {MORE.map(([slug, label, hint]) => {
            const href = `${base}/${slug}`;
            const current = path === href || path.startsWith(`${href}/`);
            return (
              <li key={slug}>
                <Link href={href} aria-current={current ? "page" : undefined}>
                  <span className="tabs__label">{label}</span>
                  <span className="tabs__hint">{hint}</span>
                </Link>
              </li>
            );
          })}
          <li>
            <Link href="/shops">
              <span className="tabs__label">Your shops</span>
              <span className="tabs__hint">Switch shop or connect another</span>
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
}
