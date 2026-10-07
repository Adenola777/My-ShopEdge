"use client";

/**
 * The pages of the area in use, as a row at the top of the page on a phone. On a larger
 * screen the rail lists them under the area instead, so the row is hidden there. Added on
 * 7 October 2026 with `lib/nav.js`, so a seller on a phone sees every page an area holds
 * without leaving it.
 *
 * A page that belongs to no area, or an area with one page, shows no row.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { hrefOf, locate } from "@/lib/nav";

/** @param {{ shopId: string }} props */
export function SectionNav({ shopId }) {
  const path = usePathname() ?? "";
  const base = `/shops/${shopId}`;
  const { area, page: current } = locate(path, base);
  const row = useRef(/** @type {HTMLUListElement | null} */ (null));
  // A page late in a long row would sit off the right edge, so the row scrolls to it.
  useEffect(() => {
    const ul = row.current;
    const on = ul?.querySelector('[aria-current="page"]');
    if (ul && on instanceof HTMLElement) ul.scrollLeft = on.offsetLeft - ul.offsetLeft - 16;
  }, [path]);
  if (!area || area.pages.length < 2) return null;
  return (
    <nav className="subnav" aria-label={`${area.label} pages`}>
      <ul ref={row}>
        {area.pages.map((page) => (
          <li key={page[0]}>
            <Link href={hrefOf(base, page[0])} aria-current={page === current ? "page" : undefined}>
              {page[1]}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
