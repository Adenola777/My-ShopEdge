"use client";

/**
 * The shop's areas, as the owner approved them from the brief on 10 October 2026 (A36.1
 * item 4). On a larger screen the sidebar lists the eight areas in the brief's order:
 * Overview, Reconcile, Products, Returns, Stock, Exports, VAT and tax, and Settings at its
 * foot. The area in use opens to list its pages. On a phone the bottom tabs are Overview,
 * Reconcile, Products, Exports and More, and the More page holds the rest (`more/page.jsx`).
 * An area's pages sit in a row at the top of the page on a phone (`SectionNav`).
 *
 * The icons are simple line drawings, so each tab is named by its word and the icon only
 * helps the eye find it.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AREAS, MORE, SETTINGS, hrefOf, locate } from "@/lib/nav";

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
  tax: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6" />
    </svg>
  ),
  returns: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 14 4 9l5-5" />
      <path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11" />
    </svg>
  ),
  exports: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v12M7.5 10.5 12 15l4.5-4.5" />
      <path d="M4 15.5v3A2.5 2.5 0 0 0 6.5 21h11a2.5 2.5 0 0 0 2.5-2.5v-3" />
    </svg>
  ),
  more: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="5.5" cy="12" r="1.2" />
      <circle cx="12" cy="12" r="1.2" />
      <circle cx="18.5" cy="12" r="1.2" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1" />
    </svg>
  ),
};

/**
 * @param {{ area: import("@/lib/nav").NavArea, base: string,
 *   here: ReturnType<typeof locate>, className?: string }} props
 */
function Area({ area, base, here, className = "" }) {
  const open = here.area === area;
  const first = area.pages[0];
  const href = hrefOf(base, first ? first[0] : area.slug);
  return (
    <div className={`tabs__area${open ? " tabs__area--open" : ""}${area.phone === "more" ? " tabs__area--rail" : ""} ${className}`}>
      <Link
        className="tabs__tab"
        href={href}
        aria-current={open && here.page === first ? "page" : open ? "true" : undefined}
      >
        {ICON[area.icon]}
        <span>{area.label}</span>
      </Link>
      {open && area.pages.length > 1 && (
        <ul className="tabs__pages" aria-label={area.label}>
          {area.pages.map((page) => (
            <li key={page[0]}>
              <Link href={hrefOf(base, page[0])} aria-current={here.page === page ? "page" : undefined}>
                {page[1]}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** @param {{ shopId: string }} props */
export function ShopNav({ shopId }) {
  const path = usePathname() ?? "";
  const base = `/shops/${shopId}`;
  const here = locate(path, base);
  // More is marked while the seller is on it or on any area it holds.
  const onMore = path === hrefOf(base, MORE) || here.area?.phone === "more";
  return (
    <nav className="tabs" aria-label="Your shop">
      {AREAS.map((area) => (
        <Area key={area.slug} area={area} base={base} here={here} />
      ))}
      <Area area={SETTINGS} base={base} here={here} className="tabs__area--settings" />
      <div className="tabs__area tabs__area--more">
        <Link className="tabs__tab" href={hrefOf(base, MORE)} aria-current={onMore ? "page" : undefined} data-testid="tab-more">
          {ICON.more}
          <span>More</span>
        </Link>
      </div>
    </nav>
  );
}
