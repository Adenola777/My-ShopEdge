"use client";

/**
 * The website's main links in the app's top bar, for a visitor who is not signed in (the
 * navigation the owner approved on 11 October 2026). Pricing and the legal pages live in the
 * app, so without these a visitor who opened Pricing lost the way back to Features and How it
 * works. Start and the sign-in screens keep a bare bar, so nothing competes with signing up.
 */

import { usePathname } from "next/navigation";
import { PRICING, SIGN_IN, SITE, START } from "@/lib/links";

const BARE = ["/start", "/handler", "/reviewer", "/connections"];

export function MarketingLinks() {
  const path = usePathname() ?? "";
  if (BARE.some((p) => path === p || path.startsWith(`${p}/`))) return null;
  const onPricing = path === PRICING;
  return (
    <nav className="appbar__site" aria-label="Main">
      <a className="appbar__sitelink" href={SITE.features}>Features</a>
      <a className="appbar__sitelink" href={SITE.how}>How it works</a>
      <a className="appbar__sitelink" href={PRICING} aria-current={onPricing ? "page" : undefined}>Pricing</a>
      <a className="appbar__login" href={SIGN_IN}>Log in</a>
      <a className="btn btn--primary btn--small appbar__start" href={START}>Start free</a>
    </nav>
  );
}
