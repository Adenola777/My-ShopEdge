"use client";

/**
 * The client halves of the setup and data screens built on 29 September 2026: S5 Tax profile,
 * S20 Manual cost entry, S4 Upload mapping, S23 Export and S31 Download my data. Every figure
 * and every rule is the service's; these components collect what the seller types, send it,
 * and show what came back.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, formatDate, formatMoney } from "@/lib/api";
import { newKey, parsePounds } from "@/lib/money-input";
import { FormError, formFailure } from "@/components/FormFailure";

/** @typedef {import("@/lib/api-types").components["schemas"]} Schemas */

/** @param {any} r @param {string} fallback @param {string} [unreachable] */
function failure(r, fallback, unreachable = "MyShopEdge could not be reached, so nothing was saved.") {
  return r.unreachable ? unreachable : (r.data?.detail ?? fallback);
}

const NO_FILE_STARTED = "MyShopEdge could not be reached, so no file was started.";

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
      setError(failure(r, "Your business details were not saved. Try again."));
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
        <label htmlFor="vat">Are you VAT registered?</label>
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
 * @typedef {{ sku_id: string, title: string, seller_sku: string | null, units: number, has_cost: boolean, cost: Schemas["Money"] | null }} CostRow
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
    let tried = 0;
    for (const [skuId, v] of Object.entries(values)) {
      if (!v.cost.trim()) continue;
      tried += 1;
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
      else errs[skuId] = failure(r, "This cost was not saved. Try again.");
    }
    setErrors(errs);
    setBusy(false);
    setMessage(saved ? `${saved} ${saved === 1 ? "cost" : "costs"} saved.`
      : tried === 0 ? "Nothing was saved, because no product cost was entered."
      : "Nothing was saved. Each product below says why.");
    if (saved) {
      // Only the rows that saved are cleared, so a row that failed keeps what was typed.
      setValues((/** @type {any} */ all) => Object.fromEntries(Object.entries(all).filter(([id]) => errs[id])));
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
              <div className="rows__sub">{r.seller_sku ?? "No seller SKU"} · {r.units} sold in the last 30 days{r.cost ? ` · current cost ${formatMoney(r.cost)}` : ""}</div>
            </div>
            <div className="cost-fields">
              {/** @type {[string, string][]} */ ([["cost", "Product cost (£)"], ["packing", "Packaging you pay (£)"], ["postage", "Shipping you pay (£)"]]).map(([f, label]) => (
                <div key={f}>
                  <label htmlFor={`${f}-${r.sku_id}`}>{label}</label>
                  <input id={`${f}-${r.sku_id}`} inputMode="decimal" placeholder={f === "cost" ? "3.40" : "Optional"}
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
      <p><button className="btn btn--primary btn--block" onClick={save} disabled={busy} data-testid="save-costs">{busy ? "Saving" : "Save costs"}</button></p>
      <p><Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/setup/tax`}>Do this later</Link></p>
    </div>
  );
}

// ---------------------------------------------------------------------------------- S4

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

/** Words for a row's outcome, used only when the service gives no reason of its own. */
/** @type {Record<string, string>} */
const OUTCOME_WORDS = {
  unmatched: "No product in your shop has this code.",
  duplicate: "This code appears more than once in your file.",
};

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
    if (!put || !put.ok) { setBusy(false); setError("Your file did not upload, so nothing was read. Check your connection and choose the file again."); return; }
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
    setError(null);
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
        <p><Link className="btn btn--primary btn--block" href={`/shops/${shopId}/setup/tax`}>Continue to your business details</Link></p>
      </div>
    );
  }

  return (
    <div className="stack" data-testid="upload-flow">
      {!upload && (
        <div className="card">
          <label htmlFor="cost-file">Your cost file, Excel or CSV</label>
          <input id="cost-file" type="file" accept=".csv,.xlsx" onChange={pick} disabled={busy} data-testid="cost-file" />
          {busy && <p className="note" role="status" data-testid="upload-reading">Uploading and reading your file.</p>}
          <p className="footnote">The file goes to MyShopEdge's private file store in the EU and is kept as the record behind your costs. MyShopEdge does not share it.</p>
        </div>
      )}
      {upload && columns.length === 0 && (
        <div className="card stack" data-testid="upload-unreadable">
          <h2>We could not read your columns</h2>
          <p>
            {upload.error
              ?? "We could not find a row of column headings in this file. The first row should name each column, such as a code column and a product cost column."}
          </p>
          <p className="footnote">
            Cost files are Excel (.xlsx) or CSV. The first row names the columns, every column
            in it needs a heading, and no two columns share a heading.
          </p>
          <p>
            <button
              type="button"
              className="btn btn--primary btn--block"
              onClick={() => { setUpload(null); setMapping(null); setMatch(null); setError(null); }}
              data-testid="try-another-file"
            >
              Choose a different file
            </button>
          </p>
        </div>
      )}
      {upload && mapping && columns.length > 0 && (
        <div className="card stack">
          <h2>Which column is which</h2>
          <div>
            <label htmlFor="match-on">The code in your file is</label>
            <select id="match-on" value={mapping.match_on} onChange={(e) => setMapping({ ...mapping, match_on: /** @type {any} */ (e.target.value) })}>
              <option value="seller_sku">Your seller SKU</option>
              <option value="tiktok_sku_id">TikTok's SKU ID</option>
            </select>
          </div>
          {picker("key_column", "Code column", false)}
          {picker("cost_column", "Product cost column", false)}
          {picker("packing_column", "Packaging you pay column", true)}
          {picker("postage_column", "Shipping you pay column", true)}
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
          <p><button className="btn btn--primary btn--block" onClick={apply} disabled={busy || !(match.rows_matched > 0)} data-testid="apply-costs">{busy ? "Applying" : `Apply ${match.rows_matched ?? 0} ${match.rows_matched === 1 ? "cost" : "costs"}`}</button></p>
          {(match.rows ?? []).some((/** @type {any} */ x) => x.outcome !== "matched") && (
            <details>
              <summary>Review unmatched rows</summary>
              <ul className="rows" data-testid="unmatched-rows">
                {match.rows.filter((/** @type {any} */ x) => x.outcome !== "matched").map((/** @type {any} */ x) => (
                  <li key={x.row_id}><span>{x.seller_sku ?? "No code"}</span><span className="muted">{x.reason ?? OUTCOME_WORDS[x.outcome] ?? "This row was not matched."}</span></li>
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
 * Fetches a fresh signed link for a ready file and follows it. A link lives fifteen minutes,
 * so one taken when the screen opened can be dead by the time the seller clicks; asking the
 * single read at the click means the button works however long the screen sat open.
 * Added 8 October 2026.
 *
 * @param {string} path  The job's single read, getExport or getAccountExport.
 * @returns {Promise<string | null>}  An error to show, or null when the download began.
 */
async function openFile(path) {
  const r = await api(path, { cache: "no-store" });
  if (r.ok && r.data?.status === "ready" && r.data.download_url) {
    window.location.assign(r.data.download_url);
    return null;
  }
  if (r.ok && r.data?.status === "expired") return "This file has expired. You can build it again.";
  return r.unreachable ? "MyShopEdge could not be reached, so the file did not download." : "The file could not be fetched. Please try again.";
}

/** @param {{ path: string, label?: string, testId?: string }} props */
function DownloadButton({ path, label = "Download", testId = "download" }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));
  return (
    <>
      <button className="btn btn--primary btn--block" disabled={busy} data-testid={testId}
        onClick={async () => { setBusy(true); setError(null); setError(await openFile(path)); setBusy(false); }}>
        {busy ? "Getting the file" : label}
      </button>
      {error && <span className="form-error" role="alert">{error}</span>}
    </>
  );
}

/**
 * Polls a job until it leaves `queued`, then offers the file. Shared by S23 and S31, because
 * A3 S31 says the data download "reuses the export flow rather than defining a second one".
 *
 * A poll that fails stops polling and says so, with a button to check again. Until
 * 9 October 2026 a failed poll stopped polling and showed nothing, so the screen sat on
 * "building" for ever.
 *
 * @param {{ path: string, job: any, onReset: () => void, onSettled?: () => void }} props
 */
function JobStatus({ path, job: first, onReset, onSettled }) {
  const [job, setJob] = useState(first);
  const [pollFailed, setPollFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (job.status !== "queued") { onSettled?.(); return; }
    if (pollFailed) return;
    const t = setTimeout(async () => {
      const r = await api(path, { cache: "no-store" });
      if (r.ok) setJob(r.data);
      else setPollFailed(true);
    }, 1500);
    return () => clearTimeout(t);
  }, [job, path, onSettled, pollFailed, attempt]);

  if (job.status === "queued" && pollFailed) {
    return (
      <div className="stack" data-testid="job-check-failed">
        <p className="note" role="status">MyShopEdge could not check on your file just now. When it last checked, the file was still being built, and it will appear in your recent files below once it is ready.</p>
        <p><button className="btn btn--quiet" data-testid="job-check-again"
          onClick={() => { setPollFailed(false); setAttempt((n) => n + 1); }}>Check again</button></p>
      </div>
    );
  }
  if (job.status === "queued") {
    return <p className="note" role="status" data-testid="job-queued">MyShopEdge is building your file. You can leave this screen and come back, and the file will be in the list below.</p>;
  }
  if (job.status === "failed") {
    return (
      <div className="stack" data-testid="job-failed">
        <p className="form-error" role="alert">MyShopEdge could not build the file. Your records are unchanged. Please try again, and if it fails a second time, email info@inspirecraftglobal.com.</p>
        <p><button className="btn btn--quiet" onClick={onReset}>Try again</button></p>
      </div>
    );
  }
  if (job.status === "expired") {
    return (
      <div className="stack" data-testid="job-expired">
        <p className="note">This file has expired. You can build it again.</p>
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
        {job.expires_at && <li><span>Kept until</span><strong>{formatDate(job.expires_at)}</strong></li>}
      </ul>
      <p><DownloadButton path={path} /></p>
      <p className="footnote">MyShopEdge keeps this file for seven days, and you can build it again whenever you need it.</p>
      <p><button className="btn btn--quiet btn--block" onClick={onReset}>Build another file</button></p>
    </div>
  );
}

/** @type {Record<string, string>} */
const JOB_STATE = { queued: "Being built", ready: "Ready", failed: "Could not be built", expired: "Expired" };

/**
 * The recent files, from listExports or listAccountExports, so a seller who left the screen
 * can come back to one. Added 8 October 2026. A list carries no link, so each Download asks
 * the single read for a fresh one, which also builds a job left queued by a restart.
 *
 * @param {{ listPath: string, itemPath: (id: string) => string, describe: (job: any) => string, version: number }} props
 */
function RecentFiles({ listPath, itemPath, describe, version }) {
  const [jobs, setJobs] = useState(/** @type {any[] | null} */ (null));
  const [failed, setFailed] = useState(false);
  const [checks, setChecks] = useState(0);
  useEffect(() => {
    let live = true;
    api(listPath, { cache: "no-store" }).then((r) => {
      if (!live) return;
      setFailed(!r.ok);
      if (r.ok) setJobs(r.data.exports);
    });
    return () => { live = false; };
  }, [listPath, version, checks]);

  if (failed) return <p className="muted" data-testid="recent-files-error">Your earlier files cannot be shown just now.</p>;
  if (!jobs || jobs.length === 0) return null;
  return (
    <div className="card" data-testid="recent-files">
      <h2>Your recent files</h2>
      <ul className="rows">
        {jobs.map((job) => (
          <li key={job.id} data-testid="recent-file">
            <span>
              {describe(job)}
              <br />
              <span className="muted">Asked for {formatDate(job.requested_at)}. {JOB_STATE[job.status] ?? job.status}.</span>
            </span>
            {job.status === "ready" ? (
              <span><DownloadButton path={itemPath(job.id)} testId="recent-download" /></span>
            ) : job.status === "queued" ? (
              <span>
                <button className="btn btn--quiet" data-testid="recent-check"
                  onClick={async () => { await api(itemPath(job.id), { cache: "no-store" }); setChecks((n) => n + 1); }}>
                  Check again
                </button>
              </span>
            ) : null}
          </li>
        ))}
      </ul>
      <p className="footnote">MyShopEdge keeps each file for seven days. You can build an expired file again.</p>
    </div>
  );
}

/** @param {{ date: Date }} p */
function iso({ date }) {
  return date.toISOString().slice(0, 10);
}

/** @type {Record<string, string>} */
const KINDS = { month_summary: "Month summary", ledger: "Ledger, every entry", transactions: "Transactions, one row per order line" };

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
  const [error, setError] = useState(/** @type {import("@/components/FormFailure").Failure | null} */ (null));
  const [version, setVersion] = useState(0);
  const settled = useCallback(() => setVersion((n) => n + 1), []);

  const range = period === "custom" ? [from, to] : /** @type {any} */ (periods)[period].slice(1);

  async function start() {
    setBusy(true);
    setError(null);
    const r = await api(`/shops/${encodeURIComponent(shopId)}/exports`, {
      method: "POST", idempotencyKey: newKey(),
      body: JSON.stringify({ kind, format, basis, period_start: range[0], period_end: range[1] }),
    });
    setBusy(false);
    if (!r.ok) { setError(formFailure(r, { fallback: "The export did not start.", unreachable: NO_FILE_STARTED })); return; }
    setJob(r.data);
    setVersion((n) => n + 1);
  }

  const shopPath = `/shops/${encodeURIComponent(shopId)}/exports`;
  const recent = (
    <RecentFiles listPath={shopPath} itemPath={(id) => `${shopPath}/${id}`} version={version}
      describe={(j) => `${KINDS[j.kind] ?? j.kind}, ${formatDate(j.period_start)} to ${formatDate(j.period_end)}, ${j.basis} basis, ${j.format === "xlsx" ? "Excel" : "CSV"}`} />
  );
  if (job) {
    return (
      <div className="stack">
        <JobStatus path={`${shopPath}/${job.id}`} job={job} onReset={() => setJob(null)} onSettled={settled} />
        {recent}
      </div>
    );
  }
  return (
    <div className="stack" data-testid="export-form">
      <div>
        <label htmlFor="kind">What to export</label>
        <select id="kind" value={kind} onChange={(e) => setKind(e.target.value)} data-testid="kind">
          {Object.entries(KINDS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="period">Period</label>
        <select id="period" value={period} onChange={(e) => setPeriod(e.target.value)} data-testid="period">
          {Object.entries(periods).map(([k, [l]]) => <option key={k} value={k}>{l}</option>)}
          <option value="custom">Custom dates</option>
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
      <p className="note">
        The file covers {formatDate(range[0])} to {formatDate(range[1])} on the {basis} basis.
        {kind === "month_summary" && " Its totals match your Overview figures for the same period and basis."}
      </p>
      <FormError failure={error} />
      <p><button className="btn btn--primary btn--block" onClick={start} disabled={busy} data-testid="start-export">{busy ? "Starting" : "Build file"}</button></p>
      {recent}
    </div>
  );
}

// ---------------------------------------------------------------------------------- S23, scheduled

/** @type {Record<number, string>} */
const WEEKDAYS = { 1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday" };

/** @param {number} n */
function ordinal(n) {
  const tail = n % 10 === 1 && n !== 11 ? "st" : n % 10 === 2 && n !== 12 ? "nd" : n % 10 === 3 && n !== 13 ? "rd" : "th";
  return `${n}${tail}`;
}

/** @param {Schemas["ExportSchedule"]} s */
function describeSchedule(s) {
  const when = s.cadence === "weekly"
    ? `every ${WEEKDAYS[s.day_of_week ?? 1]}, covering the Monday to Sunday before`
    : `on the ${ordinal(s.day_of_month ?? 1)} of each month, covering the month before`;
  return `${KINDS[s.kind] ?? s.kind}, ${s.format === "xlsx" ? "Excel" : "CSV"}, ${s.basis} basis, ${when}`;
}

/**
 * Scheduled exports (MON-8, A5.7), added 9 October 2026 on listExportSchedules,
 * createExportSchedule, updateExportSchedule and deleteExportSchedule. The daily job builds
 * each file on its day and raises a notice. Nothing sends email, because the service has no
 * email provider, so the screen promises only the notice. A weekly schedule is on the sales
 * basis only, which the service enforces and this form says.
 *
 * @param {{ shopId: string }} props
 */
export function ScheduledExports({ shopId }) {
  const path = `/shops/${encodeURIComponent(shopId)}/export-schedules`;
  const [schedules, setSchedules] = useState(/** @type {Schemas["ExportSchedule"][] | null} */ (null));
  const [loadFailed, setLoadFailed] = useState(false);
  const [version, setVersion] = useState(0);
  const [kind, setKind] = useState("month_summary");
  const [format, setFormat] = useState("xlsx");
  const [basis, setBasis] = useState("sales");
  const [cadence, setCadence] = useState("monthly");
  const [weekday, setWeekday] = useState("1");
  const [monthDay, setMonthDay] = useState("1");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  useEffect(() => {
    let live = true;
    api(path, { cache: "no-store" }).then((r) => {
      if (!live) return;
      setLoadFailed(!r.ok);
      if (r.ok) setSchedules(r.data.schedules);
    });
    return () => { live = false; };
  }, [path, version]);

  async function add() {
    setBusy(true);
    setError(null);
    const weekly = cadence === "weekly";
    const r = await api(path, {
      method: "POST", idempotencyKey: newKey(),
      body: JSON.stringify({
        kind, format, cadence, basis: weekly ? "sales" : basis,
        day_of_week: weekly ? Number(weekday) : null,
        day_of_month: weekly ? null : Number(monthDay),
      }),
    });
    setBusy(false);
    if (!r.ok) { setError(failure(r, "The schedule was not saved.")); return; }
    setVersion((n) => n + 1);
  }

  /** @param {string} id @param {any} init @param {string} fallback */
  async function change(id, init, fallback) {
    setBusy(true);
    setError(null);
    const r = await api(`${path}/${encodeURIComponent(id)}`, init);
    setBusy(false);
    if (!r.ok) setError(failure(r, fallback));
    setVersion((n) => n + 1);
  }

  return (
    <div className="card stack" data-testid="scheduled-exports">
      <h2>Scheduled exports</h2>
      <p>
        MyShopEdge can build a file for you each week or each month on the day you choose, and
        it tells you in Notifications when the file is ready. A weekly file covers the Monday to
        Sunday before it, and a monthly file covers the month before it.
      </p>
      {loadFailed ? (
        <p className="muted" data-testid="schedules-error">Your scheduled exports cannot be shown just now.</p>
      ) : schedules === null ? (
        <p className="muted" data-testid="schedules-loading">Loading your scheduled exports.</p>
      ) : schedules.length === 0 ? (
        <p className="muted" data-testid="schedules-empty">You have no scheduled exports.</p>
      ) : (
        <ul className="rows">
          {schedules.map((s) => (
            <li key={s.id} data-testid="schedule">
              <span>
                {describeSchedule(s)}
                <br />
                <span className="muted">
                  {s.active ? "Active" : "Paused"}. {s.last_run_at ? `Last built ${formatDate(s.last_run_at)}.` : "Not built yet."}
                </span>
              </span>
              <span>
                <button className="btn btn--quiet" disabled={busy} data-testid={s.active ? "schedule-pause" : "schedule-resume"}
                  onClick={() => change(s.id, { method: "PATCH", body: JSON.stringify({ active: !s.active }) },
                    s.active ? "The schedule was not paused." : "The schedule was not resumed.")}>
                  {s.active ? "Pause" : "Resume"}
                </button>{" "}
                <button className="btn btn--quiet" disabled={busy} data-testid="schedule-remove"
                  onClick={() => change(s.id, { method: "DELETE" }, "The schedule was not removed.")}>
                  Remove
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
      <h3>Add a schedule</h3>
      <div>
        <label htmlFor="sched-kind">What to export</label>
        <select id="sched-kind" value={kind} onChange={(e) => setKind(e.target.value)} data-testid="sched-kind">
          {Object.entries(KINDS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="sched-cadence">How often</label>
        <select id="sched-cadence" value={cadence} onChange={(e) => setCadence(e.target.value)} data-testid="sched-cadence">
          <option value="monthly">Every month</option>
          <option value="weekly">Every week</option>
        </select>
      </div>
      {cadence === "weekly" ? (
        <div>
          <label htmlFor="sched-weekday">On</label>
          <select id="sched-weekday" value={weekday} onChange={(e) => setWeekday(e.target.value)} data-testid="sched-weekday">
            {Object.entries(WEEKDAYS).map(([n, l]) => <option key={n} value={n}>{l}</option>)}
          </select>
        </div>
      ) : (
        <div>
          <label htmlFor="sched-day">On day</label>
          <select id="sched-day" value={monthDay} onChange={(e) => setMonthDay(e.target.value)} data-testid="sched-day">
            {Array.from({ length: 28 }, (_, i) => i + 1).map((n) => <option key={n} value={String(n)}>{ordinal(n)}</option>)}
          </select>
          <p className="footnote">The latest day offered is the 28th, so that February is never missed.</p>
        </div>
      )}
      {cadence === "weekly" ? (
        <p className="note">A weekly file is on the sales basis. MyShopEdge records the cash basis by the month a payout settled, so a week cannot be shown on the cash basis.</p>
      ) : (
        <div>
          <label htmlFor="sched-basis">Basis</label>
          <select id="sched-basis" value={basis} onChange={(e) => setBasis(e.target.value)} data-testid="sched-basis">
            <option value="sales">Sales basis, by the day of the sale</option>
            <option value="cash">Cash basis, by the settlement</option>
          </select>
        </div>
      )}
      <div>
        <label htmlFor="sched-format">Format</label>
        <select id="sched-format" value={format} onChange={(e) => setFormat(e.target.value)} data-testid="sched-format">
          <option value="xlsx">Excel</option>
          <option value="csv">CSV</option>
        </select>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <p><button className="btn btn--primary btn--block" onClick={add} disabled={busy} data-testid="add-schedule">{busy ? "Saving" : "Add the schedule"}</button></p>
      <p className="footnote">
        MyShopEdge builds a scheduled file during its morning read of your shop on the day you
        choose. Each file appears in your recent files and is kept for seven days. MyShopEdge
        tells you in Notifications and does not send an email.
      </p>
    </div>
  );
}

export function DataDownload() {
  const [job, setJob] = useState(/** @type {any} */ (null));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {import("@/components/FormFailure").Failure | null} */ (null));
  const [version, setVersion] = useState(0);
  const settled = useCallback(() => setVersion((n) => n + 1), []);
  const recent = (
    <RecentFiles listPath="/me/export" itemPath={(id) => `/me/export/${id}`} version={version}
      describe={() => "All your data, as CSV and JSON in one zip file"} />
  );

  async function start() {
    setBusy(true);
    setError(null);
    const r = await api("/me/export", { method: "POST", idempotencyKey: newKey() });
    setBusy(false);
    if (!r.ok) { setError(formFailure(r, { fallback: "The download did not start.", unreachable: NO_FILE_STARTED })); return; }
    setJob(r.data);
    setVersion((n) => n + 1);
  }

  if (job) {
    return (
      <div className="stack">
        <JobStatus path={`/me/export/${job.id}`} job={job} onReset={() => setJob(null)} onSettled={settled} />
        {recent}
      </div>
    );
  }
  return (
    <div className="stack">
      <FormError failure={error} />
      <p><button className="btn btn--primary btn--block" onClick={start} disabled={busy} data-testid="start-download">{busy ? "Starting" : "Build my data file"}</button></p>
      {recent}
    </div>
  );
}

/** Re-exported so pages can format figures the same way. */
export { formatMoney };
