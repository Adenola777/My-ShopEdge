"use client";

/**
 * Feedback for a click before the server has answered, approved by the owner on 11 October
 * 2026. Every screen fetches the service afresh, so a click waits for that trip, and until
 * this change nothing on the page moved while it did.
 *
 * Three things happen here, for the whole app, so no screen has to opt in.
 *
 * 1. A link to another page of the app takes `data-pending` the moment it is clicked, and
 *    `globals.css` gives it the selected look, so a tab lights up at once.
 * 2. If the page has not arrived after 120ms, a thin orange bar runs along the top of the
 *    window until it does. A quicker page never shows it. Next often shows the new page's
 *    loading skeleton (`RouteLoading`) at once and the figures a moment later, so the bar
 *    also runs while that skeleton is on the screen.
 * 3. A `.btn` that becomes disabled within 1.5 seconds of being pressed is the one whose action
 *    is running. It takes `data-pending` and `aria-busy`, and `globals.css` draws a spinner
 *    beside its label. Both come off when the button is enabled again or leaves the page.
 *    Forms already disable their button while they work (`busy`), so no form had to change.
 *
 * A link that opens a new tab, a download, a link with a modifier key held, and a link to the
 * same page or only to a place on it are left alone.
 */

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";

const SHOW_AFTER_MS = 120;
const GIVE_UP_MS = 10000;
const PRESS_WINDOW_MS = 1500;
const LOADING = '[data-testid="route-loading"]';

/** True while a clicked link's page or a loading skeleton is still on its way. */
function waiting() {
  return document.querySelector("a[data-pending]") !== null || document.querySelector(LOADING) !== null;
}

/** @param {MouseEvent} e @returns {HTMLAnchorElement | null} */
function internalLink(e) {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return null;
  const a = e.target instanceof Element ? e.target.closest("a[href]") : null;
  if (!(a instanceof HTMLAnchorElement)) return null;
  if ((a.target && a.target !== "_self") || a.hasAttribute("download")) return null;
  const to = new URL(a.href, window.location.href);
  if (to.origin !== window.location.origin) return null;
  if (to.pathname === window.location.pathname && to.search === window.location.search) return null;
  return a;
}

export function NavFeedback() {
  const pathname = usePathname();
  const search = useSearchParams();
  const bar = useRef(/** @type {HTMLDivElement | null} */ (null));
  const ctl = useRef({ start: () => {}, settle: () => {}, clearLinks: () => {} });

  useEffect(() => {
    /** @type {{ el: HTMLButtonElement, at: number } | null} */
    let pressed = null;
    /** @type {number | undefined} */ let showTimer;
    /** @type {number | undefined} */ let giveUpTimer;
    /** @type {number | undefined} */ let doneTimer;

    const clearLinks = () => document.querySelectorAll("a[data-pending]").forEach((el) => el.removeAttribute("data-pending"));
    const running = () => bar.current?.getAttribute("data-state") === "running";

    const stop = () => {
      window.clearTimeout(showTimer); window.clearTimeout(giveUpTimer);
      showTimer = giveUpTimer = undefined;
      bar.current?.removeAttribute("data-state");
      clearLinks();
    };

    // Something is on its way: show the bar if it is still on its way after 120ms.
    const start = () => {
      if (running() || showTimer !== undefined) return;
      window.clearTimeout(doneTimer);
      showTimer = window.setTimeout(() => {
        showTimer = undefined;
        if (waiting()) bar.current?.setAttribute("data-state", "running");
      }, SHOW_AFTER_MS);
      window.clearTimeout(giveUpTimer);
      giveUpTimer = window.setTimeout(stop, GIVE_UP_MS);
    };

    // Nothing is on its way any more: finish the bar if it was showing.
    const settle = () => {
      if (waiting()) return;
      window.clearTimeout(showTimer); window.clearTimeout(giveUpTimer);
      showTimer = giveUpTimer = undefined;
      const el = bar.current;
      if (el && running()) {
        el.setAttribute("data-state", "done");
        doneTimer = window.setTimeout(() => el.removeAttribute("data-state"), 400);
      }
    };
    ctl.current = { start, settle, clearLinks };

    /** @param {MouseEvent} e */
    const onClick = (e) => {
      const a = internalLink(e);
      if (!a) return;
      clearLinks();
      a.setAttribute("data-pending", "");
      start();
    };

    /** @param {PointerEvent | KeyboardEvent} e */
    const onPress = (e) => {
      if (e instanceof KeyboardEvent && e.key !== "Enter" && e.key !== " ") return;
      const b = e.target instanceof Element ? e.target.closest("button.btn") : null;
      if (b instanceof HTMLButtonElement && !b.disabled) pressed = { el: b, at: Date.now() };
    };

    /** @param {HTMLButtonElement} b */
    const release = (b) => { b.removeAttribute("data-pending"); b.removeAttribute("aria-busy"); };

    const watch = new MutationObserver((changes) => {
      let tree = false;
      for (const c of changes) {
        if (c.type === "childList") {
          tree = true;
          c.removedNodes.forEach((n) => {
            if (pressed && n instanceof Element && (n === pressed.el || n.contains(pressed.el))) pressed = null;
          });
          continue;
        }
        const b = c.target;
        if (!(b instanceof HTMLButtonElement)) continue;
        if (b.disabled && pressed?.el === b && Date.now() - pressed.at < PRESS_WINDOW_MS) {
          b.setAttribute("data-pending", "");
          b.setAttribute("aria-busy", "true");
        } else if (!b.disabled && b.hasAttribute("data-pending")) {
          release(b);
          if (pressed?.el === b) pressed = null;
        }
      }
      if (tree) {
        if (document.querySelector(LOADING)) start();
        else settle();
      }
    });
    watch.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["disabled"] });

    // Capture, so the click is seen before next/link calls preventDefault on it.
    document.addEventListener("click", onClick, true);
    document.addEventListener("pointerdown", onPress, true);
    document.addEventListener("keydown", onPress, true);
    return () => {
      window.clearTimeout(showTimer); window.clearTimeout(giveUpTimer); window.clearTimeout(doneTimer);
      watch.disconnect();
      document.removeEventListener("click", onClick, true);
      document.removeEventListener("pointerdown", onPress, true);
      document.removeEventListener("keydown", onPress, true);
    };
  }, []);

  // The address has changed, so the clicked link has done its work. The bar carries on while
  // the new page's skeleton is showing and finishes when it has gone.
  useEffect(() => {
    ctl.current.clearLinks();
    if (document.querySelector(LOADING)) ctl.current.start();
    else ctl.current.settle();
  }, [pathname, search]);

  return <div ref={bar} className="navbar-progress" aria-hidden="true" />;
}
