"use client";

/**
 * What a screen shows while it loads, and when it fails to render. Added 8 October 2026: the
 * copy audit found no route with a loading page or an error page, so a slow read showed the
 * previous screen and a fault showed Next's own error page.
 *
 * Each area's `loading.jsx` and `error.jsx` render these inside the area's layout, which
 * already supplies `<main>`. The error's own message is never shown to a seller, because it
 * can carry internal detail; Next logs it, and its digest is shown so a fault can be traced.
 */

import { useEffect } from "react";

/** @param {{ what?: string }} props */
export function RouteLoading({ what = "this page" }) {
  return (
    <section className="state" aria-busy="true" aria-live="polite" data-testid="route-loading">
      <p>MyShopEdge is loading {what}.</p>
    </section>
  );
}

/**
 * @param {{ error: Error & { digest?: string }, reset: () => void, home?: string }} props
 */
export function RouteError({ error, reset, home = "/shops" }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <section className="state" role="alert" data-testid="route-error">
      <h1>This page could not be shown.</h1>
      <p>Nothing on your account has changed. Try again, and if it fails again, go back to your shops.</p>
      <p>
        <button type="button" className="btn btn--primary" onClick={() => reset()}>Try again</button>
      </p>
      <p><a className="btn btn--quiet" href={home}>Go to your shops</a></p>
      {error.digest && <p className="footnote">Reference: {error.digest}</p>}
    </section>
  );
}
