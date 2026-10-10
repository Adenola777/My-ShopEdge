/**
 * The shop's navigation, in one place, so the rail, the bottom tabs and the row of pages at
 * the top of each area all read the same map. Rebuilt on 7 October 2026 at the owner's
 * request: every page sits under the area it belongs to, and Settings is an area of its
 * own rather than a list of loose links behind More.
 *
 * Each area has a path under the shop, a label, an icon name and its pages. Each page is
 * [path under the shop or an absolute path, label, further paths that also belong to it].
 * An area's first page is its overview, and its path is the area's own.
 *
 * The labels follow the owner's brief of 10 October 2026, approved that day: Today became
 * Overview, Money became Reconcile and Tax became VAT and tax. The same day the owner
 * approved the brief's eight areas (A36.1 item 4), so Returns, Stock and Exports became areas
 * of their own. The page paths did not change, so no address a seller has saved stops
 * working.
 */

/** @typedef {[string, string, string[]?]} NavPage */
/**
 * `phone` says where the area sits on a phone: `tab` is one of the four bottom tabs, and
 * `more` is a line on the More page.
 * @typedef {{ slug: string, label: string, icon: string, phone: "tab" | "more", pages: NavPage[] }} NavArea
 */

/**
 * The seven areas a seller works in, in the brief's order (A36.1 item 4, 10 October 2026).
 * On a larger screen all seven are the sidebar, with Settings at its foot. On a phone
 * Overview, Reconcile, Products and Exports are the bottom tabs with More beside them.
 * @type {NavArea[]}
 */
export const AREAS = [
  {
    slug: "today", label: "Overview", icon: "today", phone: "tab", pages: [
      ["today", "Overview"],
      ["notifications", "Notifications"],
      ["discrepancies", "Discrepancies"],
    ],
  },
  {
    slug: "money", label: "Reconcile", icon: "money", phone: "tab", pages: [
      ["money", "Where the money went", ["first-result"]],
      ["payouts", "Payouts"],
      ["records", "Transactions"],
    ],
  },
  {
    slug: "products", label: "Products", icon: "products", phone: "tab", pages: [
      ["products", "All products", ["profit-reveal"]],
      ["setup/costs", "Product costs"],
    ],
  },
  {
    slug: "returns", label: "Returns", icon: "returns", phone: "more", pages: [
      ["returns", "Returns"],
    ],
  },
  {
    slug: "stock", label: "Stock", icon: "stock", phone: "more", pages: [
      ["stock", "Stock levels"],
    ],
  },
  {
    slug: "exports", label: "Exports", icon: "exports", phone: "tab", pages: [
      ["money/export", "Exports"],
    ],
  },
  {
    slug: "tax", label: "VAT and tax", icon: "tax", phone: "more", pages: [
      ["tax", "VAT and tax overview"],
      ["setup/tax", "Business details"],
      ["other-sales", "Other-channel sales"],
    ],
  },
];

/** Settings is the eighth area: the foot of the sidebar, and a line on the More page. @type {NavArea} */
export const SETTINGS = {
  slug: "settings", label: "Settings", icon: "settings", phone: "more", pages: [
    ["settings/profile", "Profile and plan"],
    ["settings", "Shop connection", ["sync", "connection-problem", "setup", "settings/disconnect"]],
    ["settings/alerts", "Alert settings"],
    ["settings/data", "Your data", ["settings/delete"]],
    ["/shops?all=1", "Your shops"],
    ["glossary", "Help and glossary"],
  ],
};

/** The More page on a phone, which is reached from the fifth bottom tab. */
export const MORE = "more";

export const ALL_AREAS = [...AREAS, SETTINGS];

/**
 * @param {string} base `/shops/{id}`
 * @param {string} slug
 */
export function hrefOf(base, slug) {
  return slug.startsWith("/") ? slug : `${base}/${slug}`;
}

/**
 * The area and page a path belongs to. The longest matching path wins, so `money/export`
 * is Export rather than Money's overview, and `settings/alerts` is Alert settings rather than the
 * shop connection. A path that belongs to nothing gives nulls.
 *
 * @param {string} path
 * @param {string} base
 * @returns {{ area: NavArea | null, page: NavPage | null }}
 */
export function locate(path, base) {
  /** @type {{ area: NavArea | null, page: NavPage | null }} */
  let found = { area: null, page: null };
  let best = -1;
  for (const area of ALL_AREAS) {
    for (const page of area.pages) {
      for (const slug of [page[0], ...(page[2] ?? [])]) {
        if (slug.startsWith("/")) continue;
        const href = hrefOf(base, slug);
        if ((path === href || path.startsWith(`${href}/`)) && href.length > best) {
          best = href.length;
          found = { area, page };
        }
      }
    }
  }
  return found;
}
