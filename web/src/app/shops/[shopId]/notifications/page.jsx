/**
 * S13 Notifications, from wireframe sheet 08: the title, how many need the seller, an Open
 * and Resolved switch, and one row per notice with its chip.
 *
 * Open is every notice not yet `done` and Resolved is those that are. Both are filtered by
 * the service (`status=open` and `status=done`) and paged by its cursor, so a seller with a
 * long history of resolved notices never has an open one pushed off the page. Until
 * 25 September 2026 this screen fetched one page of everything and filtered it here.
 *
 * Each open notice can be marked read or done, one way, as `notifications.py` allows. The
 * page then refreshes, and so does the bell, whose count is the service's `unread_count`.
 * The owner asked on 25 September for notifications to work properly after QA found that
 * nothing could mark one read, so the bell's count could never fall.
 *
 * WFW section 4 says tapping a notice opens the relevant screen. A Notification carries
 * `type`, `shop_id`, `entity_type` and `entity_id` but no address, so since 9 October 2026
 * `noticeLink` gives a link only for the types whose writer was read in the service, and no
 * link for any other notice:
 *
 * - `stock_absorbed`, written by `_absorb` in tiktok_sync.py with `entity_type` 'sku' and the
 *   SKU's id, opens that SKU's stock movements (S26).
 * - `reconnect_needed`, written by tiktok_webhooks.py with `entity_type` 'shop' and the
 *   shop's id, opens Connection problem (S28), which offers the reconnect button.
 * - `first_read_complete` opens the shop's Today. Another change is adding that notice, and
 *   its writer was not in this tree when the link was written, so the link rests on
 *   `shop_id` alone.
 * - `order_limit_passed`, written by `notify_order_limit` in order_usage.py with no shop,
 *   because the plan's limit is the account's, opens Today of the shop whose page this is,
 *   where the order count is shown (A16.3, 9 October 2026).
 * - `low_stock`, written by `low_stock_notices` in alert_notices.py with `entity_type` 'sku'
 *   and the SKU's id, opens that SKU's stock screen (S26), as S7 links each variant.
 * - `return_unchecked`, written by `return_check_notices` in alert_notices.py with
 *   `entity_type` 'return' and the return's id, opens Check returns (S8). S8 lists every
 *   return awaiting a check on one page and has no address for one return.
 *
 * Nothing in the service writes a notice about a discrepancy today, so none links to
 * Discrepancies.
 */

import Link from "next/link";
import { api, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { MarkAllRead, NotificationActions } from "@/components/NotificationActions";
import { chipClass, SEVERITY_TONE } from "@/lib/terms";

export const metadata = { title: "Notifications" };

/** @type {Record<string, string>} */
const SEVERITY_WORD = { critical: "Act now", warning: "Check", info: "Note" };

/**
 * The screen a notice concerns, or null when that is not known. See the header for where
 * each rule comes from.
 *
 * @param {import("@/lib/api-types").components["schemas"]["Notification"]} n
 * @param {string} shopId  The shop whose page this is, used when a notice names no shop.
 * @returns {{ href: string, label: string } | null}
 */
function noticeLink(n, shopId) {
  const shop = encodeURIComponent(n.shop_id ?? shopId);
  if (n.type === "stock_absorbed" && n.entity_type === "sku" && n.entity_id) {
    return { href: `/shops/${shop}/stock/${encodeURIComponent(n.entity_id)}`, label: "See this item's stock" };
  }
  if (n.type === "reconnect_needed" && n.entity_type === "shop" && n.entity_id) {
    return { href: `/shops/${encodeURIComponent(n.entity_id)}/connection-problem`, label: "Reconnect your shop" };
  }
  if (n.type === "low_stock" && n.entity_type === "sku" && n.entity_id) {
    return { href: `/shops/${shop}/stock/${encodeURIComponent(n.entity_id)}`, label: "See this item's stock" };
  }
  if (n.type === "return_unchecked" && n.entity_type === "return") {
    return { href: `/shops/${shop}/returns`, label: "Check returns" };
  }
  if (n.type === "first_read_complete" || n.type === "order_limit_passed") {
    return { href: `/shops/${shop}/today`, label: "See Today" };
  }
  return null;
}

/**
 * @param {{
 *   params: Promise<{ shopId: string }>,
 *   searchParams: Promise<Record<string, string>>,
 * }} props
 */
export default async function NotificationsPage({ params, searchParams }) {
  const { shopId } = await params;
  const query = await searchParams;
  const resolved = query.show === "resolved";

  const q = new URLSearchParams({ status: resolved ? "done" : "open", limit: "50" });
  if (query.cursor) q.set("cursor", query.cursor);
  const result = await api(`/notifications?${q}`, { cache: "no-store" });
  const problem = apiProblem(result, { what: "your notifications" });
  if (problem) return problem;

  /** @type {{ notifications: import("@/lib/api-types").components["schemas"]["Notification"][], unread_count: number, next_cursor?: string | null }} */
  const { notifications, unread_count, next_cursor } = result.data;
  const base = `/shops/${shopId}/notifications`;
  const unreadHere = notifications.filter((n) => n.status === "unread").map((n) => n.id);

  return (
    <section>
      <header className="page-head">
        <h1>Notifications</h1>
        <p>
          {unread_count === 0
            ? "You have no unread notices."
            : `You have ${unread_count} unread ${unread_count === 1 ? "notice" : "notices"}.`}
        </p>
      </header>

      <nav className="switch" aria-label="Show">
        <Link href={base} aria-current={!resolved ? "true" : undefined}>Open</Link>
        <Link href={`${base}?show=resolved`} aria-current={resolved ? "true" : undefined}>Resolved</Link>
      </nav>

      {!resolved && <MarkAllRead ids={unreadHere} all={unreadHere.length === unread_count} />}

      {notifications.length === 0 ? (
        <section className="state">
          <h2>{resolved ? "Nothing resolved yet." : "You have no open notices."}</h2>
          <p>
            MyShopEdge tells you here when an item runs low on stock, when a return has waited
            longer than your Alerts setting for your check, when TikTok&rsquo;s stock count rises
            and MyShopEdge reduces your adjustment, or when your TikTok connection is close to
            expiring.
          </p>
        </section>
      ) : (
        <div className="card">
          <ul className="rows">
            {notifications.map((n) => {
              const link = noticeLink(n, shopId);
              return (
              <li key={n.id}>
                <span>
                  {n.status === "unread" ? <strong>{n.title}</strong> : n.title}
                  <div className="rows__sub">
                    {[n.status === "unread" ? "New" : null, n.body?.replace(/\.\s*$/, ""), formatDate(n.created_at)]
                      .filter(Boolean).join(". ")}
                  </div>
                  {link && (
                    <div><Link href={link.href} data-testid="notice-link">{link.label}</Link></div>
                  )}
                  <NotificationActions id={n.id} status={n.status} title={n.title} />
                </span>
                <span className={chipClass(SEVERITY_TONE[n.severity] ?? "quiet")}>
                  {SEVERITY_WORD[n.severity] ?? "Note"}
                </span>
              </li>
              );
            })}
          </ul>
        </div>
      )}

      {next_cursor && (
        <p className="pager">
          <Link
            className="btn btn--quiet"
            href={`${base}?${new URLSearchParams({ ...(resolved ? { show: "resolved" } : {}), cursor: next_cursor })}`}
          >
            Older notices
          </Link>
        </p>
      )}
    </section>
  );
}
