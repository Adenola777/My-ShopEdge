"use client";

/**
 * The interactive parts of three settings screens: S27 Alert settings, S29 Disconnect and
 * S24 Other-channel sales. Each is a small client component so its server page stays a
 * plain read. Every write goes through `lib/api`, so it carries the seller's token and the
 * same row-level security as any other request.
 *
 * Written by Emergent AI in `Adenola777/MYSHOPEDGE` (commit 3f1bd43, 27 September 2026) and
 * brought into this repository on 28 September at the owner's instruction, after review in
 * `audit/EMERGENT_review_28_september.md`. Changes on the way in:
 * - The delete-account and download-my-data forms are left out. Their routes are not taken:
 *   deletion erased nothing while telling the seller it had, and the download depended on
 *   Emergent's own file storage.
 * - Other-channel sales converts pounds to pence with `parsePounds`, which has no floating
 *   point step, where Emergent used `Math.round(Number(amount) * 100)` (A13 rule 3).
 * - Two style classes this stylesheet does not have (`btn--danger`, `note--ok`) are replaced
 *   with ones it does, and the props carry types so `npm run check` passes.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { newKey, parsePounds } from "@/lib/money-input";

/**
 * S27 Alert settings. A full replacement of the three thresholds.
 *
 * @param {{
 *   shopId: string,
 *   initial: { low_stock_days: number, coming_back_days: number, absorption_tolerance_units: number },
 * }} props
 */
export function AlertSettingsForm({ shopId, initial }) {
  const router = useRouter();
  const [low, setLow] = useState(String(initial.low_stock_days));
  const [coming, setComing] = useState(String(initial.coming_back_days));
  const [absorb, setAbsorb] = useState(String(initial.absorption_tolerance_units));
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  /** @param {import("react").FormEvent} e */
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    const r = await api(`/shops/${encodeURIComponent(shopId)}/alert-settings`, {
      method: "PUT",
      body: JSON.stringify({
        low_stock_days: Number(low),
        coming_back_days: Number(coming),
        absorption_tolerance_units: Number(absorb),
      }),
    });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable ? "MyShopEdge could not be reached, so nothing was saved." : (r.data?.detail ?? "Those settings were not saved."));
      return;
    }
    setSaved(true);
    router.refresh();
  }

  return (
    <form onSubmit={save} className="card stack" data-testid="alert-settings-form">
      <div>
        <label htmlFor="low">Low stock warning (days of cover)</label>
        <input id="low" data-testid="low-stock-days" inputMode="numeric" value={low}
               onChange={(e) => setLow(e.target.value)} />
        <p className="rows__sub">A variant is marked low when it has fewer than this many days of stock left.</p>
      </div>
      <div>
        <label htmlFor="coming">Coming back window (days)</label>
        <input id="coming" data-testid="coming-back-days" inputMode="numeric" value={coming}
               onChange={(e) => setComing(e.target.value)} />
      </div>
      <div>
        <label htmlFor="absorb">Absorption tolerance (units)</label>
        <input id="absorb" data-testid="absorption-tolerance" inputMode="numeric" value={absorb}
               onChange={(e) => setAbsorb(e.target.value)} />
        <p className="rows__sub">Above this, an unexplained rise in TikTok stock is raised as a discrepancy rather than absorbed quietly.</p>
      </div>
      {error && <p className="form-error" role="alert" data-testid="alert-settings-error">{error}</p>}
      {saved && <p className="note" role="status" data-testid="alert-settings-saved">Saved.</p>}
      <p><button className="btn btn--primary" data-testid="save-alert-settings" disabled={busy}>{busy ? "Saving" : "Save thresholds"}</button></p>
    </form>
  );
}

/**
 * S29 Disconnect. Confirms first, because a seller reads "disconnect" as "delete".
 *
 * @param {{ shopId: string }} props
 */
export function DisconnectAction({ shopId }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  async function disconnect() {
    setBusy(true);
    setError(null);
    const r = await api(`/shops/${encodeURIComponent(shopId)}/connection`, {
      method: "DELETE",
      idempotencyKey: newKey(),
    });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable ? "MyShopEdge could not be reached, so nothing was changed." : (r.data?.detail ?? "The shop was not disconnected."));
      return;
    }
    setDone(true);
    router.refresh();
  }

  if (done) {
    return (
      <div className="note" role="status" data-testid="disconnect-done">
        <p>Your shop is disconnected. Your records are still here, and reconnecting the same shop resumes against them.</p>
      </div>
    );
  }

  return (
    <div className="stack">
      {error && <p className="form-error" role="alert" data-testid="disconnect-error">{error}</p>}
      <p><button className="btn btn--quiet" data-testid="confirm-disconnect" onClick={disconnect} disabled={busy}>{busy ? "Disconnecting" : "Disconnect this shop"}</button></p>
    </div>
  );
}

/**
 * S24 Other-channel sales. Enter a month's total from a channel outside TikTok.
 *
 * @param {{ shopId: string }} props
 */
export function OtherSalesForm({ shopId }) {
  const router = useRouter();
  const [month, setMonth] = useState("");
  const [channel, setChannel] = useState("");
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  /** @param {import("react").FormEvent} e */
  async function save(e) {
    e.preventDefault();
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(month.trim())) {
      setError("Enter the month as YYYY-MM, for example 2026-06.");
      return;
    }
    if (channel.trim() === "") {
      setError("Name the channel, for example Etsy or eBay.");
      return;
    }
    const minor = parsePounds(amount);
    if (minor === null) {
      setError("Enter the total in pounds, for example 1234.56.");
      return;
    }
    setBusy(true);
    setError(null);
    setSaved(false);
    const r = await api(`/shops/${encodeURIComponent(shopId)}/other-sales/${month.trim()}`, {
      method: "PUT",
      body: JSON.stringify({ channel: channel.trim(), gross: { amount_minor: minor, currency: "GBP" } }),
    });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable ? "MyShopEdge could not be reached, so nothing was saved." : (r.data?.detail ?? "That figure was not saved."));
      return;
    }
    setSaved(true);
    setAmount("");
    router.refresh();
  }

  return (
    <form onSubmit={save} className="card stack" data-testid="other-sales-form">
      <div>
        <label htmlFor="os-month">Month</label>
        <input id="os-month" data-testid="other-sales-month" placeholder="2026-06" value={month}
               onChange={(e) => setMonth(e.target.value)} />
      </div>
      <div>
        <label htmlFor="os-channel">Channel</label>
        <input id="os-channel" data-testid="other-sales-channel" maxLength={100} placeholder="Etsy"
               value={channel} onChange={(e) => setChannel(e.target.value)} />
      </div>
      <div>
        <label htmlFor="os-amount">Total for the month (£)</label>
        <input id="os-amount" data-testid="other-sales-amount" inputMode="decimal" placeholder="1234.56"
               value={amount} onChange={(e) => setAmount(e.target.value)} />
      </div>
      {error && <p className="form-error" role="alert" data-testid="other-sales-error">{error}</p>}
      {saved && <p className="note" role="status" data-testid="other-sales-saved">Saved.</p>}
      <p><button className="btn btn--primary" data-testid="save-other-sales" disabled={busy}>{busy ? "Saving" : "Save month"}</button></p>
    </form>
  );
}
