"use client";

/**
 * The client halves of the setup and data screens built on 29 September 2026: S5 Tax profile,
 * S20 Manual cost entry, S4 Upload mapping, S23 Export and S31 Download my data. Every figure
 * and every rule is the service's; these components collect what the seller types, send it,
 * and show what came back.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, formatDate, formatMoney } from "@/lib/api";
import { newKey, parsePounds } from "@/lib/money-input";

/** @typedef {import("@/lib/api-types").components["schemas"]} Schemas */

/** @param {any} r @param {string} fallback */
function failure(r, fallback) {
  return r.unreachable ? "MyShopEdge could not be reached, so nothing was saved." : (r.data?.detail ?? fallback);
}

// ---------------------------------------------------------------------------------- S5

/** @param {{ shopId: string, initial: Schemas["TaxProfile"] | null }} props */
export function TaxProfileForm({ shopId, initial }) {
  const router = useRouter();
  const [structure, setStructure] = useState(initial?.business_structure ?? "");
  const [vat, setVat] = useState(initial?.vat_registered ? "yes" : "no");
  const [vatFrom, setVatFrom] = useState(initial?.vat_registered_from ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  /** @param {React.FormEvent} e */
  async function save(e) {
    e.preventDefault();
    if (vat === "yes" && !vatFrom) {
      setError("Enter the date your VAT registration started.");
      return;
    }
    setBusy(true);
    setError(null);
    const r = await api("/tax-profile", {
      method: "PUT",
      body: JSON.stringify({
        business_structure: structure || null,
        vat_registered: vat === "yes",
        vat_registered_from: vat === "yes" ? vatFrom : null,
      }),
    });
    setBusy(false);
    if (!r.ok) {
      setError(failure(r, "Your tax profile was not saved."));
      return;
    }
    router.push(`/shops/${shopId}/today`);
  }

  return (
    <form onSubmit={save} className="stack" data-testid="tax-profile-form">
      <div>
        <label htmlFor="structure">Business type</label>
        <select id="structure" value={structure} onChange={(e) => setStructure(e.target.value)} data-testid="structure">
          <option value="">Choose one</option>
          <option value="sole_trader">Sole trader</option>
          <option value="company">Limited company</option>
          <option value="not_sure">Not sure</option>
        </select>
      </div>
      <div>
        <label htmlFor="vat">VAT registered</label>
        <select id="vat" value={vat} onChange={(e) => setVat(e.target.value)} data-testid="vat">
          <option value="no">No</option>
          <option value="yes">Yes</option>
        </select>
      </div>
      {vat === "yes" && (
        <div>
          <label htmlFor="vat-from">Registered from</label>
          <input id="vat-from" type="date" value={vatFrom} onChange={(e) => setVatFrom(e.target.value)} />
        </div>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
      <p><button className="btn btn--primary btn--block" disabled={busy} data-testid="save-tax">{busy ? "Saving" : "Save and finish"}</button></p>
      <p><Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/today`} data-testid="skip-tax">Skip for now</Link></p>
    </form>
  );
}

// ---------------------------------------------------------------------------------- S20

/**
 * @typedef {{ sku_id: string, title: string, seller_sku: string | null, units: number, has_cost: boolean }} CostRow
 * @param {{ shopId: string, rows: CostRow[], currency: string }} props
 */
export function ManualCosts({ shopId, rows, currency }) {
  const router = useRouter();
  const [only, setOnly] = useState(false);
  /** @type {[Record<string, {cost: string, packing: string, postage: string, zero: boolean}>, Function]} */
  const [values, setValues] = useState({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(/** @type {string | null} */ (null));
  /** @type {[Record<string, string>, Function]} */
  const [errors, setErrors] = useState({});

  /** @param {string} id @param {string} field @param {any} v */
  function set(id, field, v) {
    setValues((/** @type {any} */ all) => ({ ...all, [id]: { cost: "", packing: "", postage: "", zero: false, ...all[id], [field]: v } }));
  }

  async function save() {
    setBusy(true);
    setMessage(null);
    /** @type {Record<string, string>} */
    const errs = {};
    let saved = 0;
    for (const [skuId, v] of Object.entries(values)) {
      if (!v.cost.trim()) continue;
      const cost = parsePounds(v.cost);
      const packing = v.packing.trim() ? parsePounds(v.packing) : undefined;
      const postage = v.postage.trim() ? parsePounds(v.postage) : undefined;
      if (cost === null || packing === null || postage === null) {
        errs[skuId] = "Enter pounds and pence, for example 3.40.";
        continue;
      }
      // CST-4 via A3 S20: a zero cost is accepted only once the seller has confirmed it.
      if (cost === 0 && !v.zero) {
        errs[skuId] = "Tick the box to confirm this costs you nothing.";
        continue;
      }
      /** @param {number | undefined} p */
      const m = (p) => (p === undefined ? undefined : { amount_minor: p, currency });
      const r = await api(`/shops/${encodeURIComponent(shopId)}/skus/${encodeURIComponent(skuId)}/cost`, {
        method: "PUT",
        idempotencyKey: newKey(),
        body: JSON.stringify({ cost: m(cost), packing: m(packing), postage: m(postage) }),
      });
      if (r.ok) saved += 1;
      else errs[skuId] = failure(r, "Not saved.");
    }
    setErrors(errs);
    setBusy(false);
    setMessage(saved ? `${saved} ${saved === 1 ? "cost" : "costs"} saved.` : "Nothing was saved.");
    if (saved) {
      setValues({});
      router.refresh();
    }
  }

  const shown = only ? rows.filter((r) => !r.has_cost) : rows;
  return (
    <div className="stack" data-testid="manual-costs">
      <label className="check">
        <input type="checkbox" checked={only} onChange={(e) => setOnly(e.target.checked)} data-testid="only-missing" />
        Only products without a cost
      </label>
      {shown.length === 0 && <p className="muted">Every product sold here has a cost.</p>}
      {shown.map((r) => {
        const v = values[r.sku_id] ?? { cost: "", packing: "", postage: "", zero: false };
        return (
          <div className="card stack" key={r.sku_id} data-testid="cost-row">
            <div>
              <strong>{r.title}</strong>
              <div className="rows__sub">{r.seller_sku ?? "No seller SKU"} · {r.units} sold in the last 30 days{r.has_cost ? " · has a cost" : ""}</div>
            </div>
            <div className="cost-fields">
              {/** @type {[string, string][]} */ ([["cost", "Product cost (£)"], ["packing", "Packing (£)"], ["postage", "Postage (£)"]]).map(([f, label]) => (
                <div key={f}>
                  <label htmlFor={`${f}-${r.sku_id}`}>{label}</label>
                  <input id={`${f}-${r.sku_id}`} inputMode="decimal" placeholder={f === "cost" ? "For example 3.40" : "Optional"}
                         value={/** @type {any} */ (v)[f]} onChange={(e) => set(r.sku_id, f, e.target.value)} />
                </div>
              ))}
            </div>
            {parsePounds(v.cost) === 0 && (
              <label className="check"><input type="checkbox" checked={v.zero} onChange={(e) => set(r.sku_id, "zero", e.target.checked)} /> This costs me nothing</label>
            )}
            {errors[r.sku_id] && <p className="form-error" role="alert">{errors[r.sku_id]}</p>}
          </div>
        );
      })}
      {message && <p className="note" role="status" data-testid="costs-message">{message}</p>}
      <p><button className="btn btn--primary btn--block" onClick={save} disabled={busy} data-testid="save-costs">{busy ? "Saving" : "Save"}</button></p>
      <p><Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/setup/tax`}>Do this later</Link></p>
    </div>
  );
}

// ---------------------------------------------------------------------------------- S4

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

/** @param {{ shopId: string }} props */
export function UploadFlow({ shopId }) {
  const router = useRouter();
  const base = `/shops/${encodeURIComponent(shopId)}/cost-uploads`;
  const [upload, setUpload] = useState(/** @type {Schemas["CostUpload"] | null} */ (null));
  const [mapping, setMapping] = useState(/** @type {Schemas["ColumnMapping"] | null} */ (null));
  const [match, setMatch] = useState(/** @type {any} */ (null));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [done, setDone] = useState(/** @type {string | null} */ (null));

  /** @param {React.ChangeEvent<HTMLInputElement>} e */
  async function pick(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const type = file.name.toLowerCase().endsWith(".csv") ? "text/csv" : file.name.toLowerCase().endsWith(".xlsx") ? XLSX : null;
    if (!type) {
      setError("Choose an Excel (.xlsx) or CSV file. Word and PDF files carry no columns to read.");
      return;
    }
    setBusy(true);
    setError(null);
    const r = await api(base, { method: "POST", idempotencyKey: newKey(),
      body: JSON.stringify({ filename: file.name, content_type: type, size_bytes: file.size }) });
    if (!r.ok) { setBusy(false); setError(failure(r, "The upload could not start.")); return; }
    const put = await fetch(r.data.upload_url, { method: "PUT", headers: { "content-type": type }, body: file }).catch(() => null);
    if (!put || !put.ok) { setBusy(false); setError("The file did not reach the file store, so nothing was read."); return; }
    const read = await api(`${base}/${r.data.upload.id}`, { cache: "no-store" });
    setBusy(false);
    if (!read.ok) { setError(failure(read, "The file could not be read.")); return; }
    setUpload(read.data);
    setMapping(read.data.suggested_mapping ?? { match_on: "seller_sku", key_column: "", cost_column: "" });
  }

  async function check() {
    if (!upload || !mapping) return;
    setBusy(true);
    setError(null);
    const m = await api(`${base}/${upload.id}/mapping`, { method: "PUT", body: JSON.stringify(mapping) });
    if (!m.ok) { setBusy(false); setError(failure(m, "The columns were not saved.")); return; }
    const r = await api(`${base}/${upload.id}/match`, { method: "POST" });
    setBusy(false);
    if (!r.ok) { setError(failure(r, "The file could not be matched.")); return; }
    setMatch(r.data);
  }

  async function apply() {
    if (!upload || !match) return;
    const ids = (match.rows ?? []).filter((/** @type {any} */ x) => x.outcome === "matched").map((/** @type {any} */ x) => x.row_id);
    setBusy(true);
    const r = await api(`${base}/${upload.id}/apply`, { method: "POST", idempotencyKey: newKey(), body: JSON.stringify({ apply_row_ids: ids }) });
    setBusy(false);
    if (!r.ok) { setError(failure(r, "The costs were not applied.")); return; }
    setDone(`${ids.length} ${ids.length === 1 ? "cost" : "costs"} applied.`);
    router.refresh();
  }

  const columns = upload?.detected_columns ?? [];
  /** @param {string} field @param {string} label @param {boolean} optional */
  const picker = (field, label, optional) => (
    <div key={field}>
      <label htmlFor={`col-${field}`}>{label}</label>
      <select id={`col-${field}`} value={/** @type {any} */ (mapping)?.[field] ?? ""} data-testid={`col-${field}`}
              onChange={(e) => setMapping((/** @type {any} */ m) => ({ ...m, [field]: e.target.value || (optional ? null : "") }))}>
        <option value="">{optional ? "Not in this file" : "Choose a column"}</option>
        {columns.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
    </div>
  );

  if (done) {
    return (
      <div className="stack" data-testid="upload-done">
        <p className="note" role="status">{done}</p>
        <p><Link className="btn btn--primary btn--block" href={`/shops/${shopId}/setup/tax`}>Continue</Link></p>
      </div>
    );
  }

  return (
    <div className="stack" data-testid="upload-flow">
      {!upload && (
        <div className="card">
          <label htmlFor="cost-file">Your cost file, Excel or CSV</label>
          <input id="cost-file" type="file" accept=".csv,.xlsx" onChange={pick} disabled={busy} data-testid="cost-file" />
          <p className="footnote">The file goes to MyShopEdge's private file store in the EU and is kept as the record behind your costs. Nobody else can open it.</p>
        </div>
      )}
      {upload && mapping && (
        <div className="card stack">
          <h2>Column mapping</h2>
          <div>
            <label htmlFor="match-on">The code in your file is</label>
            <select id="match-on" value={mapping.match_on} onChange={(e) => setMapping({ ...mapping, match_on: /** @type {any} */ (e.target.value) })}>
              <option value="seller_sku">Your seller SKU</option>
              <option value="tiktok_sku_id">TikTok's SKU ID</option>
            </select>
          </div>
          {picker("key_column", "Code column", false)}
          {picker("cost_column", "Product cost column", false)}
          {picker("packing_column", "Packing cost column", true)}
          {picker("postage_column", "Postage column", true)}
          <p><button className="btn btn--quiet btn--block" onClick={check} disabled={busy || !mapping.key_column || !mapping.cost_column} data-testid="check-match">{busy ? "Checking" : "Check the match"}</button></p>
        </div>
      )}
      {match && (
        <div className="card">
          <h2>Match result</h2>
          <ul className="rows">
            <li><span>Matched</span><strong className="chip chip--good">{match.rows_matched ?? 0} of {match.rows_total ?? 0} rows</strong></li>
            <li><span>Unmatched</span><strong className="chip chip--warn">{match.rows_unmatched ?? 0} rows</strong></li>
            <li><span>Duplicate codes</span><strong className="chip chip--warn">{match.rows_duplicate ?? 0} rows</strong></li>
          </ul>
          <p><button className="btn btn--primary btn--block" onClick={apply} disabled={busy || !(match.rows_matched > 0)} data-testid="apply-costs">Apply {match.rows_matched ?? 0} costs</button></p>
          {(match.rows ?? []).some((/** @type {any} */ x) => x.outcome !== "matched") && (
            <details>
              <summary>Review unmatched rows</summary>
              <ul className="rows" data-testid="unmatched-rows">
                {match.rows.filter((/** @type {any} */ x) => x.outcome !== "matched").map((/** @type {any} */ x) => (
                  <li key={x.row_id}><span>{x.seller_sku ?? "No code"}</span><span className="muted">{x.reason ?? x.outcome}</span></li>
                ))}
              </ul>
              <p className="footnote">These rows are not applied. Correct them in your file and upload it again.</p>
            </details>
          )}
        </div>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------------- S23 and S31

/**
 * Polls a job until it leaves `queued`, then offers the file. Shared by S23 and S31, because
 * A3 S31 says the data download "reuses the export flow rather than defining a second one".
 *
 * @param {{ path: string, job: any, onReset: () => void }} props
 */
function JobStatus({ path, job: first, onReset }) {
  const [job, setJob] = useState(first);
  useEffect(() => {
    if (job.status !== "queued") return;
    const t = setTimeout(async () => {
      const r = await api(path, { cache: "no-store" });
      if (r.ok) setJob(r.data);
    }, 1500);
    return () => clearTimeout(t);
  }, [job, path]);

  if (job.status === "queued") {
    return <p className="note" role="status" data-testid="job-queued">Building your file. You can leave this screen and come back.</p>;
  }
  if (job.status === "failed") {
    return (
      <div className="stack" data-testid="job-failed">
        <p className="form-error" role="alert">The file could not be built.</p>
        <p><button className="btn btn--quiet" onClick={onReset}>Try again</button></p>
      </div>
    );
  }
  if (job.status === "expired") {
    return (
      <div className="stack" data-testid="job-expired">
        <p className="note">This file has expired. Build it again at no cost.</p>
        <p><button className="btn btn--quiet" onClick={onReset}>Build it again</button></p>
      </div>
    );
  }
  return (
    <div className="card stack" data-testid="job-ready">
      <ul className="rows">
        {job.size_bytes != null && <li><span>Size</span><strong>{(job.size_bytes / 1024).toFixed(1)} KB</strong></li>}
        {job.row_count != null && <li><span>Rows</span><strong>{job.row_count}</strong></li>}
        {job.ready_at && <li><span>Built</span><strong>{formatDate(job.ready_at)}</strong></li>}
        {job.expires_at && <li><span>Link works until</span><strong>{formatDate(job.expires_at)}</strong></li>}
      </ul>
      <p><a className="btn btn--primary btn--block" href={job.download_url} data-testid="download">Download</a></p>
      <p className="footnote">The file lasts seven days. After that it can be built again at no cost.</p>
    </div>
  );
}

/** @param {{ date: Date }} p */
function iso({ date }) {
  return date.toISOString().slice(0, 10);
}

/** @param {{ shopId: string, today: string }} props */
export function ExportForm({ shopId, today }) {
  const t = new Date(`${today}T12:00:00Z`);
  const monthStart = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), 1));
  const lastStart = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth() - 1, 1));
  const lastEnd = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), 0));
  const taxYear = new Date(Date.UTC(t < new Date(Date.UTC(t.getUTCFullYear(), 3, 6)) ? t.getUTCFullYear() - 1 : t.getUTCFullYear(), 3, 6));
  const periods = {
    this_month: ["This month", iso({ date: monthStart }), today],
    last_month: ["Last month", iso({ date: lastStart }), iso({ date: lastEnd })],
    tax_year: ["Tax year to date", iso({ date: taxYear }), today],
  };
  const [kind, setKind] = useState("month_summary");
  const [period, setPeriod] = useState("last_month");
  const [from, setFrom] = useState(periods.last_month[1]);
  const [to, setTo] = useState(periods.last_month[2]);
  const [basis, setBasis] = useState("sales");
  const [format, setFormat] = useState("xlsx");
  const [job, setJob] = useState(/** @type {any} */ (null));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  const range = period === "custom" ? [from, to] : /** @type {any} */ (periods)[period].slice(1);

  async function start() {
    setBusy(true);
    setError(null);
    const r = await api(`/shops/${encodeURIComponent(shopId)}/exports`, {
      method: "POST", idempotencyKey: newKey(),
      body: JSON.stringify({ kind, format, basis, period_start: range[0], period_end: range[1] }),
    });
    setBusy(false);
    if (!r.ok) { setError(failure(r, "The export did not start.")); return; }
    setJob(r.data);
  }

  if (job) {
    return <JobStatus path={`/shops/${encodeURIComponent(shopId)}/exports/${job.id}`} job={job} onReset={() => setJob(null)} />;
  }
  const kinds = { month_summary: "Month summary", ledger: "Ledger, every entry", transactions: "Transactions, one row per order line" };
  return (
    <div className="stack" data-testid="export-form">
      <div>
        <label htmlFor="kind">What to export</label>
        <select id="kind" value={kind} onChange={(e) => setKind(e.target.value)} data-testid="kind">
          {Object.entries(kinds).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="period">Period</label>
        <select id="period" value={period} onChange={(e) => setPeriod(e.target.value)} data-testid="period">
          {Object.entries(periods).map(([k, [l]]) => <option key={k} value={k}>{l}</option>)}
          <option value="custom">Choose dates</option>
        </select>
      </div>
      {period === "custom" && (
        <div className="cost-fields">
          <div><label htmlFor="from">From</label><input id="from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></div>
          <div><label htmlFor="to">To</label><input id="to" type="date" value={to} onChange={(e) => setTo(e.target.value)} /></div>
        </div>
      )}
      <div>
        <label htmlFor="basis">Basis</label>
        <select id="basis" value={basis} onChange={(e) => setBasis(e.target.value)} data-testid="basis">
          <option value="sales">Sales basis, by the day of the sale</option>
          <option value="cash">Cash basis, by the settlement</option>
        </select>
      </div>
      <div>
        <label htmlFor="format">Format</label>
        <select id="format" value={format} onChange={(e) => setFormat(e.target.value)} data-testid="format">
          <option value="xlsx">Excel</option>
          <option value="csv">CSV</option>
        </select>
      </div>
      <p className="note">The file covers {range[0]} to {range[1]} on the {basis} basis, and its totals equal the screen for the same period.</p>
      {error && <p className="form-error" role="alert">{error}</p>}
      <p><button className="btn btn--primary btn--block" onClick={start} disabled={busy} data-testid="start-export">{busy ? "Starting" : "Build the file"}</button></p>
    </div>
  );
}

export function DataDownload() {
  const [job, setJob] = useState(/** @type {any} */ (null));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  async function start() {
    setBusy(true);
    setError(null);
    const r = await api("/me/export", { method: "POST", idempotencyKey: newKey() });
    setBusy(false);
    if (!r.ok) { setError(failure(r, "The download did not start.")); return; }
    setJob(r.data);
  }

  if (job) return <JobStatus path={`/me/export/${job.id}`} job={job} onReset={() => setJob(null)} />;
  return (
    <div className="stack">
      {error && <p className="form-error" role="alert">{error}</p>}
      <p><button className="btn btn--primary btn--block" onClick={start} disabled={busy} data-testid="start-download">{busy ? "Starting" : "Prepare my data"}</button></p>
    </div>
  );
}

/** Re-exported so pages can format figures the same way. */
export { formatMoney };
