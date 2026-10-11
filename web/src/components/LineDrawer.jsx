"use client";

/**
 * One line of "Where the money went", opening its records in a side panel (A37 phase 2,
 * 11 October 2026). On a larger screen the panel slides in from the right; on a phone it
 * fills the screen. It is a native <dialog> opened with showModal, so focus stays inside it
 * while it is open, Escape closes it, and focus returns to the line that opened it.
 *
 * The line is still a link to the Transactions page, so a seller without JavaScript, or one
 * who opens it in a new tab, reaches the same records. The panel shows the first page of
 * records and its total, and links to the full page for the rest.
 */

import Link from "next/link";
import { useRef, useState } from "react";
import { api, formatDate } from "@/lib/api";
import { Figure } from "@/components/Figure";

/**
 * @param {{ href: string, path: string, label: React.ReactNode, title: string }} props
 *   `href` is the Transactions page for the line, `path` the service path with its query.
 */
export function LineDrawer({ href, path, label, title }) {
  const dialog = useRef(/** @type {HTMLDialogElement | null} */ (null));
  const [state, setState] = useState(/** @type {"idle" | "loading" | "ready" | "failed" | "locked"} */ ("idle"));
  const [page, setPage] = useState(/** @type {any} */ (null));

  /** @param {React.MouseEvent} e */
  async function open(e) {
    // A modified click keeps its usual meaning, such as opening the page in a new tab.
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    dialog.current?.showModal();
    if (state === "ready") return;
    setState("loading");
    const r = await api(path, { cache: "no-store" });
    if (r.ok && r.data) {
      setPage(r.data);
      setState("ready");
    } else if (r.status === 403 && r.data?.code === "plan_upgrade_required") {
      // A38: the records behind a figure are Starter's. Said plainly, never as a failure.
      setState("locked");
    } else {
      setState("failed");
    }
  }

  function close() {
    dialog.current?.close();
  }

  /** A click on the dimmed backdrop, outside the panel, closes it. @param {React.MouseEvent} e */
  function onBackdrop(e) {
    if (e.target === dialog.current) close();
  }

  return (
    <>
      <Link className="rowlink rowlink--quiet" href={href} onClick={open} aria-haspopup="dialog">
        {label}
      </Link>
      <dialog ref={dialog} className="drawer" aria-label={title} onClick={onBackdrop}>
        <div className="drawer__panel">
          <header className="drawer__head">
            <h2>{title}</h2>
            <button type="button" className="drawer__close" onClick={close} aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                <path d="M6 6l12 12M18 6 6 18" />
              </svg>
            </button>
          </header>
          {state === "loading" && (
            <ul className="rows" aria-busy="true">
              {[0, 1, 2].map((i) => <li key={i}><span className="skeleton">Loading the records</span><span className="skeleton">£0.00</span></li>)}
            </ul>
          )}
          {state === "locked" && (
            <div className="locked" data-testid="drawer-locked">
              <p className="locked__head">The records behind each figure are available on Starter.</p>
              <p className="rows__sub">You can already see the total on the Overview.</p>
              <Link className="btn btn--primary btn--small" href="/pricing?plan=starter">Upgrade to Starter</Link>
            </div>
          )}
          {state === "failed" && (
            <p className="muted" role="status">These records cannot be shown just now. <Link href={href}>Open the full list</Link></p>
          )}
          {state === "ready" && page && (
            page.entries.length === 0 ? (
              <p className="muted">Nothing recorded in this period.</p>
            ) : (
              <>
                <ul className="rows" aria-label={`Records behind ${title}`}>
                  {page.entries.map((/** @type {any} */ e) => (
                    <li key={e.id}>
                      {/* The line's name is the panel's title, so a record repeats it only
                          where it differs, as a shared category's fields do. */}
                      <span>
                        {formatDate(e.basis_day)}
                        <span className="rows__sub" style={{ display: "block" }}>
                          {e.tiktok_order_id ? `Order ${e.tiktok_order_id}` : e.tiktok_invoice_number ? `Invoice ${e.tiktok_invoice_number}` : "No order"}
                          {e.label && e.label !== title ? ` · ${e.label}` : ""}
                        </span>
                      </span>
                      <Figure amount={e.amount} />
                    </li>
                  ))}
                  <li className="rows__total"><span>Total</span><Figure amount={page.total} /></li>
                </ul>
                <p className="drawer__foot">
                  <Link className="btn btn--quiet btn--block" href={href}>
                    {page.next_cursor ? "View every record" : "Open as a page"}
                  </Link>
                </p>
              </>
            )
          )}
        </div>
      </dialog>
    </>
  );
}
