/**
 * S12 Tax. The VAT threshold monitor (TAX-2), the set-aside estimate (TAX-3) and the key
 * Self Assessment dates (TAX-4). Every figure is served, never worked out here. VAT is out
 * of scope as a filing feature (A29.8); this monitors a threshold and shows dates only.
 *
 * Written by Emergent AI in `Adenola777/MYSHOPEDGE` (commit 3f1bd43) and brought into this
 * repository on 28 September 2026 at the owner's instruction. See
 * `audit/EMERGENT_review_28_september.md`. The one change on the way in replaces
 * `chip--ok`, which this stylesheet does not have, with `chip--good`. On 28 September the
 * set-aside card was changed to show the service's reason and basis lines, when A30.3's
 * estimate was built.
 *
 * Since 10 October 2026 (A36 step 6, the brief's section 17) the VAT card shows the rolling
 * twelve months, this month, the dated threshold, the amount remaining, a progress bar from
 * the service's `share_of_threshold`, and when it was worked out, in calm words that state no
 * legal duty. The brief's "approaching" state is not shown, because no ruling sets where
 * approaching begins. The tax card carries the brief's heading when costs are missing and its
 * disclaimer.
 */

import Link from "next/link";
import { api, fetchShop, formatDate, formatMoney } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";

export const metadata = { title: "VAT and tax" };

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function TaxPage({ params }) {
  const { shopId } = await params;
  const [vatRes, setAsideRes, datesRes] = await Promise.all([
    fetchShop(shopId, "/tax/vat"),
    fetchShop(shopId, "/tax/set-aside"),
    api("/tax/dates", { cache: "no-store" }),
  ]);
  // Found 28 September: production's reference_rules is empty, so getVatMonitor answers 503
  // vat_unconfigured and this screen used to show only an error. A missing rule now empties
  // its own card. A session, access or network fault still stops the screen.
  const vatUnconfigured = vatRes.status === 503;
  const problem = vatUnconfigured ? null : apiProblem(vatRes, { what: "your VAT position" });
  if (problem) return problem;

  const vat = vatUnconfigured ? null : vatRes.data;
  const setAside = setAsideRes.ok ? setAsideRes.data : null;
  /** @type {{ rule_key: string, label: string, date: string, reviewed_at?: string | null }[]} */
  const dates = datesRes.ok ? (datesRes.data.dates ?? []) : [];

  return (
    <section data-testid="tax-screen">
      <header className="page-head">
        <h1>VAT and tax</h1>
        <p>VAT threshold and tax to set aside.</p>
      </header>

      <div className="stack">
        <div className="card" data-testid="vat-monitor">
          <h2>VAT registration threshold</h2>
          <p className="card__why">Last 12 months of sales against the threshold.</p>
          {!vat ? (
            <p className="muted" data-testid="vat-unconfigured">
              The VAT threshold is not loaded yet, so your position cannot be shown.
            </p>
          ) : (<>
          {(() => {
            const last = vat.months?.[vat.months.length - 1];
            const share = vat.share_of_threshold;
            return (
              <>
                <ul className="rows">
                  <li><span>Rolling twelve-month taxable turnover</span><Figure amount={vat.rolling_twelve_month_turnover} /></li>
                  {last && <li><span>TikTok sales this month so far</span><Figure amount={last.tiktok_gross} /></li>}
                  {last && last.other_channels_gross.amount_minor !== 0 && (
                    <li><span>Other-channel sales this month</span><Figure amount={last.other_channels_gross} /></li>
                  )}
                  <li>
                    <span>
                      VAT registration threshold
                      {vat.reviewed_at && <div className="rows__sub">Checked against gov.uk on {formatDate(vat.reviewed_at)}</div>}
                    </span>
                    <Figure amount={vat.threshold} />
                  </li>
                  <li className="rows__total">
                    <span>{vat.above_threshold ? "Above the threshold by" : "Amount remaining before the threshold"}</span>
                    <span className={vat.above_threshold ? "chip chip--warn" : "chip chip--good"}>
                      {formatMoney(vat.above_threshold
                        ? { amount_minor: -vat.headroom.amount_minor, currency: vat.headroom.currency }
                        : vat.headroom)}
                    </span>
                  </li>
                </ul>
                {share != null && (
                  <div className="meter" role="img" data-testid="vat-meter"
                       aria-label={`${(share * 100).toFixed(1)} per cent of the threshold`}>
                    <span style={{ width: `${Math.min(share, 1) * 100}%` }} />
                  </div>
                )}
                <p className="card__why" data-testid="vat-status">
                  {vat.above_threshold
                    ? "Above the threshold. Check HMRC's guidance or ask an accountant."
                    : "Below the threshold."}{" "}
                  Worked out {formatDate(vat.as_of, { time: true })}
                </p>
              </>
            );
          })()}
          <p className="card__foot">
            {vat.includes_other_channels
              ? "Includes your other-channel sales."
              : (<>TikTok sales only. <Link href={`/shops/${shopId}/other-sales`}>Add other-channel sales</Link></>)}
          </p>
          </>)}
        </div>

        {/* Until 9 October 2026 a failed set-aside read removed the card without a word
            (copy audit finding 110). */}
        {!setAside && (
          <div className="card" data-testid="set-aside-error">
            <h2>Estimated Income Tax and National Insurance reserve</h2>
            <p className="muted">
              MyShopEdge could not load the set-aside estimate just now. Nothing on your account
              has changed, and the other figures on this page are unaffected. Try again in a moment.
            </p>
          </div>
        )}

        {setAside && (
          <div className="card" data-testid="set-aside">
            <h2>Estimated Income Tax and National Insurance reserve</h2>
            <p className="card__why">
              To keep back for tax
              {setAside.period ? `, ${formatDate(setAside.period.from)} to ${formatDate(setAside.period.to)}` : ""}
            </p>
            {/* The reason and the basis are the service's own words (A30.3), so the card
                cannot describe a company, a missing cost or unloaded rates wrongly. */}
            <p className="hero__value"><Figure amount={setAside.amount} reason={
              (setAside.basis_of_estimate ?? [])[0]?.label ?? "No amount can be produced yet."
            } /></p>
            {/* The way to the missing input, keyed on the contract's own reason codes. */}
            {setAside.unavailable_reason === "no_tax_profile" && (
              <p className="card__foot"><Link href={`/shops/${shopId}/setup/tax`}>Fill in your business details</Link></p>
            )}
            {setAside.unavailable_reason === "incomplete_costs" && (
              <div data-testid="set-aside-costs">
                <h3>Add product costs for a more useful tax estimate.</h3>
                <p className="card__why">
                  We can track turnover and net proceeds now. Add product costs before relying on
                  a profit-based tax reserve.
                </p>
                <p className="card__foot"><Link href={`/shops/${shopId}/products`}>Add product costs</Link></p>
              </div>
            )}
            {setAside.amount && (
              <ul className="rows">
                {(setAside.basis_of_estimate ?? []).map((/** @type {NonNullable<import("@/lib/api-types").components["schemas"]["SetAside"]["basis_of_estimate"]>[number]} */ b) => (
                  b.amount
                    ? <li key={b.label}><span>{b.label}</span><strong>{formatMoney(b.amount)}</strong></li>
                    : <li key={b.label}><span className="muted">{b.label}</span></li>
                ))}
              </ul>
            )}
            <p className="footnote">An estimate, not tax advice.</p>
          </div>
        )}

        <div className="card" data-testid="tax-dates">
          <h2>Key tax dates</h2>
          <p className="card__why">The Self Assessment dates for the current tax year.</p>
          {dates.length === 0 ? (
            <p className="muted">
              {datesRes.ok ? "Tax dates are not loaded yet." : "Tax dates could not be loaded just now."}
            </p>
          ) : (
            <ul className="rows">
              {dates.map((d) => (
                <li key={d.rule_key}>
                  <span>
                    {d.label}
                    {d.reviewed_at && <div className="rows__sub">Reviewed {formatDate(d.reviewed_at)}</div>}
                  </span>
                  <strong>{formatDate(d.date)}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
