/**
 * S41 Profile and plan. Built 7 October 2026, when Settings became an area of its own at
 * the owner's request. It shows who is signed in from getMe and the plan from
 * getSubscription, and gathers the things that belong to the account rather than to a shop:
 * changing plan, signing out and deleting the account.
 *
 * The name and email come from the sign-in provider, so nothing here edits them. Changing
 * the card is not offered, because the contract has no operation for it (as S38 says). A
 * value whose request fails is shown as not available rather than guessed.
 */

import Link from "next/link";
import { api, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { chipClass } from "@/lib/terms";

export const metadata = { title: "Profile and plan" };

/** @type {Record<string, [string, string]>} */
const STATUS = {
  trialing: ["Free trial", "good"],
  active: ["Active", "good"],
  past_due: ["Payment did not go through", "critical"],
  canceled: ["Ended", "quiet"],
  none: ["No plan yet", "warn"],
};

/** @param {string | null | undefined} slug */
function planName(slug) {
  return slug ? slug.charAt(0).toUpperCase() + slug.slice(1) : "";
}

/**
 * The one line that says what happens next to the plan, from the fields getSubscription
 * returns and nothing worked out here.
 *
 * @param {import("@/lib/api-types").components["schemas"]["Subscription"]} sub
 * @returns {[string, string] | null}
 */
function nextStep(sub) {
  if (sub.status === "trialing" && sub.trial_ends_at) {
    return [sub.cancel_at_period_end ? "Trial ends, with no charge" : "First payment", formatDate(sub.trial_ends_at)];
  }
  if (sub.status === "active" && sub.current_period_end) {
    return [sub.cancel_at_period_end ? "Plan ends" : "Renews", formatDate(sub.current_period_end)];
  }
  return null;
}

/** @param {{ params: Promise<{ shopId: string }> }} props */
export default async function ProfilePage({ params }) {
  const { shopId } = await params;
  const base = `/shops/${shopId}`;
  const [meRes, subRes] = await Promise.all([
    api("/me", { cache: "no-store" }),
    api("/billing/subscription", { cache: "no-store" }),
  ]);
  const problem = apiProblem(meRes, { what: "your profile" });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["Account"]} */
  const me = meRes.data;
  /** @type {import("@/lib/api-types").components["schemas"]["Subscription"] | null} */
  const sub = subRes.ok ? subRes.data : null;
  const [statusLabel, statusTone] = sub ? (STATUS[sub.status] ?? [sub.status, "quiet"]) : ["Not available", "quiet"];
  const next = sub ? nextStep(sub) : null;
  const unavailable = <span className="muted">Not available</span>;

  return (
    <section data-testid="profile-page">
      <header className="page-head">
        <h1>Profile and plan</h1>
        <p>Your sign-in details and the plan this account is on.</p>
      </header>
      <div className="stack">
        <div className="card" data-testid="profile-account">
          <h2>You</h2>
          <ul className="rows">
            <li><span>Name</span>{me.display_name ? <strong>{me.display_name}</strong> : <span className="muted">Not given</span>}</li>
            <li><span>Email</span><strong>{me.email}</strong></li>
            <li><span>Member since</span><strong>{formatDate(me.created_at)}</strong></li>
            <li><span>Shops</span><strong>{me.shop_count ?? 0}</strong></li>
          </ul>
          <p className="card__why">Your name and email come from the way you sign in, so they change there.</p>
        </div>

        <div className="card" data-testid="profile-plan">
          <h2>Your plan</h2>
          <ul className="rows">
            <li><span>Plan</span>{sub ? <strong>{sub.plan ? planName(sub.plan) : "None"}</strong> : unavailable}</li>
            <li><span>Status</span><span className={chipClass(statusTone)}>{statusLabel}</span></li>
            {next && <li><span>{next[0]}</span><strong>{next[1]}</strong></li>}
            {sub?.card_last4 && <li><span>Card</span><strong>Ending {sub.card_last4}</strong></li>}
          </ul>
          {sub?.status === "none" || sub?.status === "canceled" ? (
            <p><Link className="btn btn--primary btn--block" href="/billing">Choose a plan</Link></p>
          ) : null}
          {sub?.status === "past_due" ? (
            <p><Link className="btn btn--primary btn--block" href="/billing/payment-failed">See what happened</Link></p>
          ) : null}
        </div>

        <p><a className="btn btn--quiet btn--block" href="/handler/sign-out" data-testid="profile-sign-out">Sign out</a></p>
        <p>
          <Link className="btn btn--quiet btn--block" href={`${base}/settings/delete`} data-testid="settings-delete">
            Delete my account
          </Link>
        </p>
        <p className="footnote">Your account closes at once and is erased after thirty days. Until then you can sign in and keep it.</p>
      </div>
    </section>
  );
}
