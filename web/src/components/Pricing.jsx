"use client";

/**
 * The pricing page and its cart, A38 (11 October 2026), built to the owner's pricing and
 * checkout specification of that day. Top to bottom: the upgrade banner for a signed-in seller
 * below Pro, the current plan, the billing-cycle selector, the four plan cards, the full
 * comparison, the FAQ and the trust points. "Buy now" opens the cart, which states exactly what
 * is being bought before anything is paid.
 *
 * Every price is the service's (`listPlans`). Checkout opens a cycle only when the service says
 * its Stripe price exists (`available`); until the owner approves the prices none does, so the
 * cart says checkout is not open yet and nothing is charged (A38.3).
 *
 * @typedef {import("@/lib/api-types").components["schemas"]} Schemas
 * @typedef {Schemas["Plan"]} Plan
 * @typedef {Schemas["Subscription"]} Subscription
 * @typedef {import("@/lib/plans").Cycle} Cycle
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, formatDate } from "@/lib/api";
import {
  BANNERS, CART_LINES, COMMITMENT_LINE, COMPARISON, CYCLES, CYCLE_LABEL, FAQ, TRUST,
  VAT_LINE, cardPrice, cartPrice, priceFor, rank, unlockPlan,
} from "@/lib/plans";

/**
 * @param {{
 *   plans: Plan[],
 *   defaultCycle: Cycle,
 *   sub: Subscription | null,
 *   email: string | null,
 *   signedIn: boolean,
 *   initialPlan?: string | null,
 *   initialCycle?: Cycle | null,
 *   manageHref: string,
 * }} props
 */
export function Pricing({ plans, defaultCycle, sub, email, signedIn, initialPlan = null, initialCycle = null, manageHref }) {
  const [cycle, setCycle] = useState(/** @type {Cycle} */ (initialCycle ?? defaultCycle));
  const [cartPlan, setCartPlan] = useState(/** @type {string | null} */ (null));
  const [downgrade, setDowngrade] = useState(false);
  const current = signedIn ? (sub?.effective_plan ?? "explorer") : null;
  const live = Boolean(sub && ["trialing", "active", "past_due"].includes(sub.status));
  const byslug = Object.fromEntries(plans.map((p) => [p.slug, p]));

  // A plan named in the address, as an upgrade prompt links, opens its cart on arrival.
  useEffect(() => {
    if (initialPlan && byslug[initialPlan] && !byslug[initialPlan].free && initialPlan !== current) {
      setCartPlan(initialPlan);
    }
    // Only on arrival.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** @param {string} slug */
  function choose(slug) {
    if (slug === "explorer") {
      if (!signedIn) window.location.assign("/start");
      else if (live) setDowngrade(true);
      return;
    }
    setCartPlan(slug);
  }

  const banner = current ? BANNERS[current] : null;

  return (
    <div className="pricing">
      {banner && (
        <aside className="pricing-banner" aria-label="Upgrade">
          <div>
            <p className="pricing-banner__title">{banner.title}</p>
            <p className="pricing-banner__body">{banner.body}</p>
          </div>
          <button type="button" className="btn btn--primary" onClick={() => choose(banner.to)}
                  data-testid="banner-upgrade">
            Switch to {byslug[banner.to]?.name}
          </button>
        </aside>
      )}

      <header className="page-head pricing__head">
        <h1>Plans and pricing</h1>
        <p>Every plan lets you add product costs. Starter adds margin and full payout detail. Growth adds exports and up to 3 shops. Pro adds unlimited orders and up to 10 shops.</p>
      </header>

      {current && <CurrentPlan plan={byslug[current]} sub={sub} live={live} manageHref={manageHref} />}

      <CycleSelector cycle={cycle} onChange={setCycle} />

      <div className="plan-grid" role="list" aria-label="Plans">
        {plans.map((plan) => (
          <PlanCard key={plan.slug} plan={plan} cycle={cycle} current={current} signedIn={signedIn}
                    onChoose={() => choose(plan.slug)} />
        ))}
      </div>

      <Comparison plans={plans} current={current} />

      <section className="pricing__section" aria-labelledby="faq-title">
        <h2 id="faq-title" className="overview__heading">Questions</h2>
        <div className="card faq">
          {FAQ.map(([q, a]) => (
            <details key={q} className="faq__item">
              <summary>{q}</summary>
              <p>{a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="pricing__section" aria-labelledby="trust-title">
        <h2 id="trust-title" className="overview__heading">Trust and security</h2>
        <ul className="trust">
          {TRUST.map(([title, text]) => (
            <li key={title} className="card trust__item">
              <p className="trust__title">{title}</p>
              <p className="trust__text">{text}</p>
            </li>
          ))}
        </ul>
      </section>

      {cartPlan && byslug[cartPlan] && (
        <Cart plan={byslug[cartPlan]} cycle={cycle} onCycle={setCycle} onClose={() => setCartPlan(null)}
              email={email} signedIn={signedIn} sub={sub} live={live} current={current}
              currentName={current ? byslug[current]?.name ?? "" : ""} />
      )}
      {downgrade && sub && (
        <DowngradeDialog sub={sub} onClose={() => setDowngrade(false)} />
      )}
    </div>
  );
}

/**
 * @param {{ plan: Plan | undefined, sub: Subscription | null, live: boolean, manageHref: string }} props
 */
function CurrentPlan({ plan, sub, live, manageHref }) {
  if (!plan) return null;
  const cycle = sub?.cycle ? CYCLE_LABEL[/** @type {Cycle} */ (sub.cycle)] : null;
  const end = sub?.status === "trialing" ? sub?.trial_ends_at : sub?.current_period_end;
  return (
    <section className="card current-plan" aria-label="Your current plan" data-testid="current-plan">
      <div>
        <p className="current-plan__label">Current plan</p>
        <p className="current-plan__name">
          {plan.name}
          <span className="current-plan__detail">
            {" · "}
            {plan.free ? "Free" : sub?.status === "trialing" ? "Free trial" : cycle ?? "Paid plan"}
          </span>
        </p>
        {live && end && (
          <p className="current-plan__renew">
            {sub?.cancel_at_period_end ? "Ends" : sub?.status === "trialing" ? "Trial ends" : "Renews"} {formatDate(end)}
          </p>
        )}
      </div>
      {live && <Link className="btn btn--quiet btn--small" href={manageHref}>Manage subscription</Link>}
    </section>
  );
}

/** @param {{ cycle: Cycle, onChange: (c: Cycle) => void, name?: string }} props */
function CycleSelector({ cycle, onChange, name = "cycle" }) {
  return (
    <fieldset className="cycle" data-testid={`${name}-selector`}>
      <legend className="cycle__legend">Billing cycle</legend>
      <div className="switch switch--compact cycle__switch">
        {CYCLES.map((c) => (
          <label key={c} className="cycle__option" aria-current={cycle === c ? "true" : undefined}>
            <input type="radio" className="visually-hidden" name={name} value={c}
                   checked={cycle === c} onChange={() => onChange(c)} />
            {CYCLE_LABEL[c]}
            {c === "annual" && <span className="cycle__save"> Save 2 months</span>}
          </label>
        ))}
      </div>
      <p className="cycle__note">
        {cycle === "annual" && "Best value. Billed once a year. "}
        {cycle === "annual_monthly" && "12 payments, billed monthly. "}
        {cycle === "monthly" && "Billed monthly. Cancel anytime. "}
        {VAT_LINE}
      </p>
      {cycle === "annual_monthly" && <p className="cycle__commitment" data-testid="commitment">{COMMITMENT_LINE}</p>}
    </fieldset>
  );
}

/**
 * The button a card shows, by the seller's current plan, as the specification sets out.
 *
 * @param {Plan} plan
 * @param {string | null} current
 * @param {boolean} signedIn
 */
function buttonLabel(plan, current, signedIn) {
  if (!signedIn || !current) return plan.free ? "Get started free" : "Buy now";
  if (plan.slug === current) return "Your current plan";
  if (plan.free) return "Downgrade to Explorer";
  return rank(plan.slug) > rank(current) ? "Buy now" : `Switch to ${plan.name}`;
}

/**
 * @param {{ plan: Plan, cycle: Cycle, current: string | null, signedIn: boolean, onChoose: () => void }} props
 */
function PlanCard({ plan, cycle, current, signedIn, onChoose }) {
  const price = cardPrice(plan, cycle);
  const mine = current === plan.slug;
  const label = buttonLabel(plan, current, signedIn);
  return (
    <div role="listitem" className={`card plan-card${plan.highlight ? " plan-card--popular" : ""}${mine ? " plan-card--current" : ""}`}
             aria-labelledby={`plan-${plan.slug}-name`} data-testid={`plan-card-${plan.slug}`}>
      <div className="plan-card__badges">
        {mine && <span className="chip chip--quiet plan-card__current">Current</span>}
        {plan.highlight && <span className="plan-card__popular">Most popular</span>}
      </div>
      <h2 id={`plan-${plan.slug}-name`} className="plan-card__name">{plan.name}</h2>
      <p className="plan-card__price">
        <span className="plan-card__amount">{price.amount}</span>
        {price.per && <span className="plan-card__per">{price.per}</span>}
      </p>
      <p className="plan-card__note">{price.note}</p>
      <p className="plan-card__audience">{plan.audience}</p>
      <ul className="plan-card__features">
        {plan.features.map((f) => <li key={f}>{f}</li>)}
        {plan.coming_soon.map((f) => (
          <li key={f} className="plan-card__soon">{f} <span className="soon">Coming soon</span></li>
        ))}
      </ul>
      <p className="plan-card__action">
        {mine ? (
          <span className="btn btn--quiet btn--block plan-card__mine" aria-disabled="true">Your current plan</span>
        ) : plan.free && !signedIn ? (
          <Link className="btn btn--quiet btn--block" href="/start" data-testid="plan-explorer-start">{label}</Link>
        ) : (
          <button type="button" className={`btn btn--block ${plan.free ? "btn--quiet" : "btn--primary"}`}
                  onClick={onChoose} data-testid={`plan-${plan.slug}-buy`}
                  aria-label={`${label}: ${plan.name}`}>
            {label}
          </button>
        )}
      </p>
    </div>
  );
}

/** @param {{ plans: Plan[], current: string | null }} props */
function Comparison({ plans, current }) {
  return (
    <section className="pricing__section" aria-labelledby="compare-title">
      <h2 id="compare-title" className="overview__heading">Compare plans</h2>
      {/* On a phone the table scrolls sideways, so it takes focus for keyboard scrolling. */}
      <div className="card compare" tabIndex={0} role="region" aria-label="Compare plans, table">
        <table className="compare__table">
          <caption className="visually-hidden">What each plan includes</caption>
          <thead>
            <tr>
              <th scope="col"><span className="visually-hidden">Feature</span></th>
              {plans.map((p) => (
                <th key={p.slug} scope="col" className={current === p.slug ? "compare__current" : undefined}>
                  {p.name}{current === p.slug && <span className="visually-hidden">, your current plan</span>}
                </th>
              ))}
            </tr>
          </thead>
          {COMPARISON.map((section) => (
            <tbody key={section.title}>
              <tr className="compare__section"><th scope="colgroup" colSpan={5}>{section.title}</th></tr>
              {section.rows.map((row) => (
                <tr key={row.name}>
                  <th scope="row">{row.name}</th>
                  {row.cells.map((cell, i) => (
                    <td key={i} className={current === plans[i]?.slug ? "compare__current" : undefined}>
                      <CellMark cell={cell} unlock={unlockPlan(row) ?? "Pro"} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
    </section>
  );
}

/** @param {{ cell: import("@/lib/plans").Cell, unlock: string }} props */
function CellMark({ cell, unlock }) {
  if (cell === "yes") return <span className="mark mark--yes"><span aria-hidden="true">✓</span><span className="visually-hidden">Included</span></span>;
  if (cell === "no") return <span className="mark mark--no"><span aria-hidden="true">–</span><span className="visually-hidden">Not included</span></span>;
  if (cell === "soon") return <span className="soon">Coming soon</span>;
  if ("text" in cell) return <span className="mark mark--text">{cell.text}</span>;
  return (
    <span className="mark mark--lock">
      <LockIcon />
      {cell.lock && <span>{cell.lock}</span>}
      <span className="visually-hidden">Available on {unlock}</span>
    </span>
  );
}

export function LockIcon() {
  return (
    <svg className="lock" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

/**
 * The cart. A native dialog, so focus stays inside it while it is open and Escape closes it.
 *
 * @param {{ plan: Plan, cycle: Cycle, onCycle: (c: Cycle) => void, onClose: () => void,
 *   email: string | null, signedIn: boolean, sub: Subscription | null, live: boolean,
 *   current: string | null, currentName: string }} props
 */
function Cart({ plan, cycle, onCycle, onClose, email, signedIn, sub, live, current, currentName }) {
  const ref = useRef(/** @type {HTMLDialogElement | null} */ (null));
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [done, setDone] = useState(/** @type {string | null} */ (null));
  useEffect(() => {
    const d = ref.current;
    if (d && !d.open) d.showModal();
    return () => { if (d?.open) d.close(); };
  }, []);

  const price = cartPrice(plan, cycle);
  const p = priceFor(plan, cycle);
  const open = Boolean(p?.available);
  const paidNow = live && current !== null && current !== "explorer";
  const upgrading = paidNow && rank(plan.slug) > rank(current);
  const switching = paidNow && rank(plan.slug) < rank(current);

  async function checkout() {
    if (!signedIn) { router.push(`/start?${new URLSearchParams({ next: `/pricing?plan=${plan.slug}&cycle=${cycle}` })}`); return; }
    if (!open) return;
    if (!live) { router.push(`/billing?${new URLSearchParams({ plan: plan.slug, cycle })}`); return; }
    setBusy(true);
    setError(null);
    const r = await api("/billing/subscription", { method: "PATCH", body: JSON.stringify({ plan: plan.slug, cycle }) });
    setBusy(false);
    if (!r.ok) {
      setError(r.data?.detail ?? "Your plan was not changed and nothing was charged. Try again in a moment.");
      return;
    }
    setDone(plan.slug === "growth" ? "Growth is active. Exports and up to 3 shops are now available."
      : plan.slug === "pro" ? "Pro is active. Up to 10 shops and unlimited orders are now available."
      : `${plan.name} is active.`);
    router.refresh();
  }

  return (
    <dialog ref={ref} className="drawer cart" aria-labelledby="cart-title" onClose={onClose}
            onClick={(e) => { if (e.target === ref.current) ref.current?.close(); }} data-testid="cart">
      <div className="drawer__panel">
        <header className="drawer__head">
          <h2 id="cart-title">Your cart</h2>
          <button type="button" className="drawer__close" onClick={() => ref.current?.close()} aria-label="Close the cart">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </header>
        {signedIn && email && <p className="cart__who">Signed in as {email}</p>}

        {done ? (
          <div role="status" className="cart__done" data-testid="cart-done">
            <p className="overview__clear"><span aria-hidden="true">✓</span> {done}</p>
            <button type="button" className="btn btn--quiet btn--block" onClick={() => ref.current?.close()}>Close</button>
          </div>
        ) : (
          <>
            <div className="cart__item">
              <p className="cart__product">MyShopEdge {plan.name}</p>
              <p className="cart__cycle">{CYCLE_LABEL[cycle]}</p>
              <ul className="cart__lines">
                {(CART_LINES[plan.slug] ?? []).map((l) => <li key={l}>{l}</li>)}
              </ul>
              <p className="cart__total" data-testid="cart-total">{price.total}</p>
              <p className="cart__how">{price.how}</p>
              <p className="cart__vat">{VAT_LINE}</p>
            </div>

            {upgrading && (
              <p className="note note--info" data-testid="cart-upgrade">
                You are upgrading from {currentName} to {plan.name}. Your new plan starts immediately.
                Any unused time on your current plan will be prorated.
              </p>
            )}
            {switching && (
              <p className="note note--info" data-testid="cart-switch">
                You are switching from {currentName} to {plan.name}. Your data stays. {plan.name}&apos;s
                shop, order and export limits apply{sub?.current_period_end ? `, and exports stay available until ${formatDate(sub.current_period_end)}` : ""}.
              </p>
            )}

            <CycleSelector cycle={cycle} onChange={onCycle} name="cart-cycle" />

            {error && <p className="form-error" role="alert">{error}</p>}
            <button type="button" className="btn btn--primary btn--block" onClick={checkout}
                    disabled={busy || (signedIn && !open)} data-testid="checkout"
                    aria-describedby="checkout-note">
              {busy ? "Changing your plan" : "Continue to checkout"}
            </button>
            <p id="checkout-note" className="cart__secure">
              <LockIcon /> {signedIn && !open ? "Secure checkout opens soon. Nothing is charged today." : "Secure checkout"}
            </p>
          </>
        )}
      </div>
    </dialog>
  );
}

/**
 * Downgrade to Explorer: the plan stops renewing, and the seller keeps it to the end of what
 * they paid for. Nothing is deleted.
 *
 * @param {{ sub: Subscription, onClose: () => void }} props
 */
function DowngradeDialog({ sub, onClose }) {
  const ref = useRef(/** @type {HTMLDialogElement | null} */ (null));
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(/** @type {string | null} */ (null));
  const [error, setError] = useState(/** @type {string | null} */ (null));
  useEffect(() => {
    const d = ref.current;
    if (d && !d.open) d.showModal();
    return () => { if (d?.open) d.close(); };
  }, []);
  const end = sub.status === "trialing" ? sub.trial_ends_at : sub.current_period_end;

  async function confirm() {
    setBusy(true);
    setError(null);
    const r = await api("/billing/subscription", { method: "PATCH", body: JSON.stringify({ cancel_at_period_end: true }) });
    setBusy(false);
    if (!r.ok) { setError(r.data?.detail ?? "Your plan was not changed. Try again in a moment."); return; }
    setMsg(end ? `Your plan stays until ${formatDate(end)}, then you move to Explorer.` : "You will move to Explorer at the end of your plan.");
    router.refresh();
  }

  return (
    <dialog ref={ref} className="drawer cart" aria-labelledby="down-title" onClose={onClose} data-testid="downgrade">
      <div className="drawer__panel">
        <header className="drawer__head">
          <h2 id="down-title">Downgrade to Explorer</h2>
          <button type="button" className="drawer__close" onClick={() => ref.current?.close()} aria-label="Close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </header>
        {msg ? (
          <p role="status" className="overview__clear"><span aria-hidden="true">✓</span> {msg}</p>
        ) : (
          <>
            <p>Your plan stops renewing{end ? ` and runs until ${formatDate(end)}` : ""}. Then Explorer&apos;s limits apply: 1 TikTok Shop, 100 orders a month and no exports.</p>
            <p>Your data stays. Nothing is deleted without your confirmation.</p>
            {error && <p className="form-error" role="alert">{error}</p>}
            <p className="upload__actions">
              <button type="button" className="btn btn--primary" onClick={confirm} disabled={busy}>
                {busy ? "Saving" : "Downgrade to Explorer"}
              </button>
              <button type="button" className="btn btn--quiet" onClick={() => ref.current?.close()}>Keep my plan</button>
            </p>
          </>
        )}
      </div>
    </dialog>
  );
}
