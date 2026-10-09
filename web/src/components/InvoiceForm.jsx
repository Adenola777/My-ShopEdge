"use client";

/**
 * The form on Payout detail for the TikTok fee invoice, built 7 October 2026.
 *
 * TikTok offers no API for a seller's fee invoices (A9.8), so the seller copies them from
 * Seller Center. The service is the authority on whether an invoice adds up: it refuses a
 * gross that is not net plus VAT and says why, and this form shows that answer. The form
 * reads pounds as text into pence (`parsePounds`) and does no other arithmetic.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { newKey, parsePounds } from "@/lib/money-input";

/** @typedef {import("@/lib/api-types").components["schemas"]["SettlementInvoice"]} Invoice */

/** @param {{ amount_minor: number }} m */
const pounds = (m) => (m.amount_minor / 100).toFixed(2);

/**
 * @param {{ shopId: string, settlementId: string, currency: string, invoice: Invoice | null }} props
 */
export function InvoiceForm({ shopId, settlementId, currency, invoice }) {
  const router = useRouter();
  const [open, setOpen] = useState(!invoice);
  const [f, setF] = useState({
    invoice_number: invoice?.invoice_number ?? "",
    invoice_type: invoice?.invoice_type ?? "",
    issued_on: invoice?.issued_on ?? "",
    period_start: invoice?.period_start ?? "",
    period_end: invoice?.period_end ?? "",
    net: invoice ? pounds(invoice.net) : "",
    vat: invoice ? pounds(invoice.vat) : "",
    gross: invoice ? pounds(invoice.gross) : "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [key] = useState(() => newKey());
  const [saved, setSaved] = useState(false);

  /** @param {keyof typeof f} name */
  const bind = (name) => ({
    id: `invoice-${name}`,
    value: f[name],
    /** @param {import("react").ChangeEvent<HTMLInputElement>} e */
    onChange: (e) => setF({ ...f, [name]: e.target.value }),
  });

  /** @param {import("react").FormEvent} e */
  async function save(e) {
    e.preventDefault();
    const amounts = { net: parsePounds(f.net), vat: parsePounds(f.vat), gross: parsePounds(f.gross) };
    if (Object.values(amounts).some((v) => v === null)) {
      setError("Enter the net, VAT and gross in pounds, for example 12.50. Enter 0 for no VAT.");
      return;
    }
    if (!f.invoice_number.trim() || !f.invoice_type.trim() || !f.issued_on) {
      setError("Enter the invoice number, its type and the date it was issued.");
      return;
    }
    const money = (/** @type {number | null} */ n) => ({ amount_minor: n ?? 0, currency });
    setBusy(true);
    setError(null);
    const r = await api(`/shops/${encodeURIComponent(shopId)}/settlements/${encodeURIComponent(settlementId)}/invoice`, {
      method: "PUT",
      idempotencyKey: key,
      body: JSON.stringify({
        invoice_number: f.invoice_number.trim(),
        invoice_type: f.invoice_type.trim(),
        issued_on: f.issued_on,
        ...(f.period_start ? { period_start: f.period_start } : {}),
        ...(f.period_end ? { period_end: f.period_end } : {}),
        net: money(amounts.net),
        vat: money(amounts.vat),
        gross: money(amounts.gross),
      }),
    });
    setBusy(false);
    if (!r.ok) {
      setError(r.unreachable ? "MyShopEdge could not be reached, so nothing was saved." : (r.data?.detail ?? "The invoice was not saved. Check the figures and try again."));
      return;
    }
    setSaved(true);
    setOpen(false);
    router.refresh();
  }

  if (!open) {
    return (
      <>
        {saved && <p className="rows__sub" role="status">The invoice is saved.</p>}
        <p><button type="button" className="btn btn--quiet btn--block" onClick={() => { setSaved(false); setOpen(true); }} data-testid="edit-invoice">
          Edit this invoice
        </button></p>
      </>
    );
  }

  return (
    <form onSubmit={save} className="stack" data-testid="invoice-form">
      <div><label htmlFor="invoice-invoice_number">Invoice number</label><input {...bind("invoice_number")} maxLength={64} /></div>
      <div><label htmlFor="invoice-invoice_type">Type, as the invoice names it</label>
        <input {...bind("invoice_type")} maxLength={120} /></div>
      <div><label htmlFor="invoice-issued_on">Date issued</label><input type="date" {...bind("issued_on")} /></div>
      <div><label htmlFor="invoice-period_start">Period from (optional)</label><input type="date" {...bind("period_start")} /></div>
      <div><label htmlFor="invoice-period_end">Period to (optional)</label><input type="date" {...bind("period_end")} /></div>
      <div><label htmlFor="invoice-net">Net (£)</label><input inputMode="decimal" placeholder="0.00" {...bind("net")} /></div>
      <div><label htmlFor="invoice-vat">VAT (£)</label><input inputMode="decimal" placeholder="0.00" {...bind("vat")} /></div>
      <div><label htmlFor="invoice-gross">Gross (£)</label><input inputMode="decimal" placeholder="0.00" {...bind("gross")} /></div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <p><button className="btn btn--primary btn--block" disabled={busy} data-testid="save-invoice">
        {busy ? "Saving" : "Save invoice"}
      </button></p>
      <p className="footnote">MyShopEdge checks that the gross equals the net plus the VAT, and keeps these figures. It does not keep a copy of the PDF.</p>
    </form>
  );
}
