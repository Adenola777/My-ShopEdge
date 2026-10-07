/**
 * The shop's navigation, in one place, so the rail, the bottom tabs and the row of pages at
 * the top of each area all read the same map. Rebuilt on 7 October 2026 at the owner's
 * request: every page sits under the area it belongs to, and Settings is an area of its
 * own rather than a list of loose links behind More.
 *
 * Each area has a path under the shop, a label, an icon name and its pages. Each page is
 * [path under the shop or an absolute path, label, further paths that also belong to it].
 * An area's first page is its overview, and its path is the area's own.
 */

/** @typedef {[string, string, string[]?]} NavPage */
/** @typedef {{ slug: string, label: string, icon: string, pages: NavPage[] }} NavArea */

/** The five areas a seller works in. They are the bottom tabs on a phone. @type {NavArea[]} */
export const AREAS = [
  {
    slug: "today", label: "Today", icon: "today", pages: [
      ["today", "Overview"],
      ["notifications", "Notifications"],
      ["discrepancies", "Discrepancies"],
    ],
  },
  {
    slug: "stock", label: "Stock", icon: "stock", pages: [
      ["stock", "Stock levels"],
      ["returns", "Returns"],
    ],
  },
  {
    slug: "products", label: "Products", icon: "products", pages: [
      ["products", "All products"],
      ["setup/costs", "Product costs"],
    ],
  },
  {
    slug: "money", label: "Money", icon: "money", pages: [
      ["money", "Overview"],
      ["payouts", "Payouts and invoices"],
      ["records", "Records"],
      ["money/export", "Export"],
    ],
  },
  {
    slug: "tax", label: "Tax", icon: "tax", pages: [
      ["tax", "Overview"],
      ["setup/tax", "Business details"],
      ["other-sales", "Other-channel sales"],
    ],
  },
];

/** Settings is reached from the gear in the top bar, and sits apart in the rail. @type {NavArea} */
export const SETTINGS = {
  slug: "settings", label: "Settings", icon: "settings", pages: [
    ["settings/profile", "Profile and plan"],
    ["settings", "Shop connection", ["sync", "connection-problem", "setup", "settings/disconnect"]],
    ["settings/alerts", "Alerts"],
    ["settings/data", "Your data", ["settings/delete"]],
    ["/shops", "Your shops"],
    ["glossary", "Help and glossary"],
  ],
};

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
 * is Export rather than Money's overview, and `settings/alerts` is Alerts rather than the
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
