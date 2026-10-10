"use client";

/**
 * "Not now" on an upgrade prompt. It goes back to the page the seller came from, or to
 * `fallback` when the prompt was the first page opened.
 */

import { useRouter } from "next/navigation";

/** @param {{ fallback: string }} props */
export function NotNow({ fallback }) {
  const router = useRouter();
  return (
    <button type="button" className="btn btn--quiet" data-testid="upgrade-not-now"
      onClick={() => (window.history.length > 1 ? router.back() : router.push(fallback))}>
      Not now
    </button>
  );
}
