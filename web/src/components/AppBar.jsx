/**
 * The top bar on every screen (WFW 1.1): the logo on the left, and inside a shop the
 * Updated stamp and the notification bell on the right.
 *
 * Settings sits here rather than among the tabs, as wireframe sheet 09 places it, so the
 * five tabs stay the five the wireframes carry. Since 7 October 2026 the gear opens the
 * Settings area at its first page, Profile and plan.
 *
 * The logo is `mse-logo-horizontal-notagline.svg` from `brand/`, drawn at 48 px high, which
 * makes it 129 px wide. A7.6 allows the lockup without the tagline from 110 px wide, and
 * forbids setting the wordmark in a font or setting the tagline on its own, which is what
 * this bar did until 24 September.
 *
 * The Updated stamp is `freshness.last_synced_at` from TodayView, the one freshness the
 * service computes (A29.3). The bell count is `unread_count` from listNotifications. Both
 * are read, never worked out here (A29.1). If either request fails, its part of the bar is
 * left out rather than shown as a guess.
 */

import { api } from "@/lib/api";

const TIME = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/London",
  hour: "2-digit",
  minute: "2-digit",
});
const DAY = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/London",
  day: "numeric",
  month: "short",
});
const LONDON_DAY = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/London" });

/** "09:12" today, "23 Sep" before today, both in London time. */
function stamp(/** @type {string} */ iso) {
  const at = new Date(iso);
  return LONDON_DAY.format(at) === LONDON_DAY.format(new Date()) ? TIME.format(at) : DAY.format(at);
}

/**
 * @param {{ shopId?: string, shopsLink?: boolean }} props `shopsLink` puts a way back to the
 *   seller's shops in the bar on screens outside a shop, so no screen is a dead end.
 */
export async function AppBar({ shopId, shopsLink = false }) {
  let freshness = null;
  let unread = null;
  if (shopId) {
    const id = encodeURIComponent(shopId);
    const [today, notes] = await Promise.all([
      api(`/shops/${id}/today`, { cache: "no-store" }),
      api("/notifications?status=unread&limit=1", { cache: "no-store" }),
    ]);
    if (today.ok) freshness = today.data?.freshness ?? null;
    if (notes.ok) unread = Number(notes.data?.unread_count ?? 0);
  }

  return (
    <header className="appbar">
      <div className="appbar__inner">
        <a className="appbar__logo" href="/">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/mse-logo-horizontal-notagline.svg" alt="MyShopEdge home" width={129} height={48} />
        </a>
        {shopId && (
          <div className="appbar__status">
            {freshness && (
              <span
                className={`appbar__updated${freshness.status === "stale" ? " appbar__updated--stale" : ""}`}
              >
                {freshness.last_synced_at
                  ? `Updated ${stamp(freshness.last_synced_at)}${freshness.status === "stale" ? ", now out of date" : ""}`
                  : "Not updated yet"}
              </span>
            )}
            <a
              className="bell"
              href={`/shops/${encodeURIComponent(shopId)}/notifications`}
              aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z" />
                <path d="M10 20.5a2 2 0 0 0 4 0" />
              </svg>
              <span className="bell__label">Notifications</span>
              {unread ? <span className="bell__dot">{unread > 9 ? "9+" : unread}</span> : null}
            </a>
            <a
              className="bell"
              href={`/shops/${encodeURIComponent(shopId)}/settings/profile`}
              aria-label="Settings"
              data-testid="appbar-settings"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="3" />
                <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" />
              </svg>
              <span className="bell__label">Settings</span>
            </a>
          </div>
        )}
        {!shopId && shopsLink && (
          <div className="appbar__status">
            <a className="appbar__link" href="/shops?all=1">Your shops</a>
          </div>
        )}
      </div>
    </header>
  );
}
