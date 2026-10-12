/**
 * The paging control at the foot of a long list (11 October 2026, the owner's check of every
 * direction control). Lists page by the service's cursor, which only moves forward, so the
 * control offers the next page and, once past the first, a way back to the start. Both carry
 * an arrow and sit in a labelled navigation region, so a screen reader announces them as one.
 */

import Link from "next/link";

/**
 * @param {{ next?: string | null, first?: string | null, nextLabel?: string, label?: string }} props
 *   `next` and `first` are the two addresses; either is left out when it does not apply.
 */
export function Pager({ next, first, nextLabel = "Next page", label = "Pages" }) {
  if (!next && !first) return null;
  return (
    <nav className="pager" aria-label={label}>
      {first && (
        <Link className="btn btn--quiet pager__first" href={first}>
          <span aria-hidden="true">&larr;</span> First page
        </Link>
      )}
      {next && (
        <Link className="btn btn--quiet pager__next" href={next} rel="next">
          {nextLabel} <span aria-hidden="true">&rarr;</span>
        </Link>
      )}
    </nav>
  );
}
