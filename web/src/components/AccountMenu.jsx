"use client";

/**
 * The account menu at the right of the top bar for a signed-in seller (the navigation the
 * owner approved on 11 October 2026): the plan, pricing, help, the way back to the website,
 * and Sign out. It closes on a choice, a click outside or Escape.
 */

import { useEffect, useRef } from "react";
import { PRICING, SIGN_OUT, SITE } from "@/lib/links";

/** @param {{ shopId?: string }} props */
export function AccountMenu({ shopId }) {
  const ref = useRef(/** @type {HTMLDetailsElement | null} */ (null));
  useEffect(() => {
    /** @param {MouseEvent} e */
    const onClick = (e) => {
      const el = ref.current;
      if (el?.open && e.target instanceof Node && !el.contains(e.target)) el.open = false;
    };
    /** @param {KeyboardEvent} e */
    const onKey = (e) => {
      const el = ref.current;
      if (e.key === "Escape" && el?.open) { el.open = false; el.querySelector("summary")?.focus(); }
    };
    document.addEventListener("click", onClick);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("click", onClick); document.removeEventListener("keydown", onKey); };
  }, []);

  const base = shopId ? `/shops/${encodeURIComponent(shopId)}` : null;
  /** @type {[string, string][]} */
  const items = [
    ...(base ? /** @type {[string, string][]} */ ([[`${base}/settings/profile`, "Account and plan"]]) : []),
    ["/shops?all=1", "Your shops"],
    [PRICING, "Plans and pricing"],
    ...(base ? /** @type {[string, string][]} */ ([[`${base}/glossary`, "Help and glossary"]]) : []),
    [SITE.home, "Back to the website"],
  ];
  return (
    <details className="acct" ref={ref} data-testid="account-menu">
      <summary aria-label="Account menu">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="12" cy="8.5" r="3.5" />
          <path d="M5 19.5c1.2-3.3 4-5 7-5s5.8 1.7 7 5" />
        </svg>
        <span className="acct__label">Account</span>
      </summary>
      <div className="acct__panel">
        {items.map(([href, label]) => (
          <a key={href} href={href} onClick={() => { if (ref.current) ref.current.open = false; }}>{label}</a>
        ))}
        <a className="acct__out" href={SIGN_OUT}>Sign out</a>
      </div>
    </details>
  );
}
