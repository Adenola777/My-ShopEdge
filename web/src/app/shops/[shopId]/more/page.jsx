/**
 * More, the fifth bottom tab on a phone (A36.1 item 4, approved 10 October 2026). It holds
 * the areas that are not bottom tabs, in the brief's order, then Notifications, Settings,
 * the glossary and Sign out. On a larger screen the sidebar lists every area, so this page
 * is not linked there, but it still works if it is opened.
 */

import Link from "next/link";
import { AREAS, SETTINGS, hrefOf } from "@/lib/nav";

export const metadata = { title: "More" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function MorePage({ params }) {
  const { shopId } = await params;
  const base = `/shops/${shopId}`;
  /** @type {[string, string][]} */
  const links = [
    ...AREAS.filter((a) => a.phone === "more").map((a) => /** @type {[string, string]} */ ([hrefOf(base, a.pages[0]?.[0] ?? a.slug), a.label])),
    [hrefOf(base, "notifications"), "Notifications"],
    [hrefOf(base, SETTINGS.pages[0]?.[0] ?? SETTINGS.slug), SETTINGS.label],
    [hrefOf(base, "glossary"), "Help and glossary"],
  ];
  return (
    <section data-testid="more">
      <header className="page-head">
        <h1>More</h1>
      </header>
      <ul className="card morelist">
        {links.map(([href, label]) => (
          <li key={href}>
            <Link href={href}>{label}</Link>
          </li>
        ))}
        <li>
          <a href="/handler/sign-out" data-testid="more-sign-out">Sign out</a>
        </li>
      </ul>
    </section>
  );
}
