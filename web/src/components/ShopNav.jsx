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
  payouts: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="6" width="18" height="13" rx="2" />
      <path d="M3 10h18M7 15h3" />
    </svg>
  ),
  records: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />
    </svg>
  ),
  costs: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v12M7 10l5 5 5-5M4 19h16" />
    </svg>
  ),
  returns: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 14 4 9l5-5M4 9h11a5 5 0 0 1 0 10h-3" />
    </svg>
  ),
  notifications: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15zM10 20.5a2 2 0 0 0 4 0" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1" />
    </svg>
  ),
  shops: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 9.5 5.5 4h13L20 9.5M4 9.5h16v10.5H4zM9.5 20v-5h5v5" />
    </svg>
  ),
  help: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17h.01" />
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
 * Everything else a seller needs, in three groups so the list reads at a glance: what
 * happened to the money, what happened to the stock, and the account itself. On a phone
 * these sit behind More, each with one line saying what it is for, because five tabs is
 * what fits across a phone. On a larger screen they are listed in the rail under the tabs,
 * with the same icon and row as a tab and without the extra line. First added 30 September
 * 2026 at the owner's request, and grouped on 7 October 2026 because one flat list of eight
 * read as clutter.
 *
 * Each item is [path under the shop, or an absolute path, label, hint, icon].
 *
 * @type {[string, [string, string, string, string][]][]}
 */
const MORE = [
  ["Money", [
    ["payouts", "Payouts", "What TikTok paid out, and each fee invoice", "payouts"],
    ["records", "Records", "Every transaction behind the figures", "records"],
  ]],
  ["Stock", [
    ["setup/costs", "Product costs", "Upload a cost file or type costs in", "costs"],
    ["returns", "Returns", "Check what came back and whether it can be resold", "returns"],
  ]],
  ["Account", [
    ["notifications", "Notifications", "What needs your attention", "notifications"],
    ["settings", "Settings", "Your shop connection, alerts and data", "settings"],
    ["/shops", "Your shops", "Switch shop or connect another", "shops"],
    ["glossary", "Help and glossary", "What each figure and word means", "help"],
  ]],
];

/** @param {{ shopId: string }} props */
export function ShopNav({ shopId }) {
  const path = usePathname() ?? "";
  const base = `/shops/${shopId}`;
  const [open, setOpen] = useState(false);
  // A new screen closes the sheet, so it never covers the page it opened.
  useEffect(() => setOpen(false), [path]);
  /** @param {string} slug */
  const hrefOf = (slug) => (slug.startsWith("/") ? slug : `${base}/${slug}`);
  const moreCurrent = MORE.some(([, items]) => items.some(([slug]) =>
    !slug.startsWith("/") && (path === hrefOf(slug) || path.startsWith(`${hrefOf(slug)}/`))));
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
        {MORE.map(([group, items]) => (
          <section key={group} className="tabs__group" aria-label={group}>
            <p className="tabs__heading">{group}</p>
            <ul>
              {items.map(([slug, label, hint, icon]) => {
                const href = hrefOf(slug);
                const current = !slug.startsWith("/") && (path === href || path.startsWith(`${href}/`));
                return (
                  <li key={slug}>
                    <Link href={href} aria-current={current ? "page" : undefined} title={hint}>
                      {ICON[icon]}
                      <span className="tabs__text">
                        <span className="tabs__label">{label}</span>
                        <span className="tabs__hint">{hint}</span>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
    </nav>
  );
}
