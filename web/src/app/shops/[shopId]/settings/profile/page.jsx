/**
 * S41 Profile and plan. Built 7 October 2026, when Settings became an area of its own at
 * the owner's request. It shows who is signed in from getMe and the plan from
 * getSubscription, and gathers the things that belong to the account rather than to a shop:
 * changing plan, signing out and deleting the account.
 *
 * The name and email come from the sign-in provider, so nothing here edits them. Since
 * 8 October 2026 a live plan also shows PlanControls, which stops or restores renewal through
 * updateSubscription and links to /billing/card for a new card. A value whose request fails
 * is shown as not available rather than guessed. Since 9 October 2026 an account whose
 * subscription status is `none` sees one line saying it has no plan, and the Choose a plan
 * button, in place of a Plan row that read "None". Since 10 October 2026 it also shows
 * EmailNoticesSwitch, the seller's switch for notice emails (NTF-2).
 */

import Link from "next/link";
import { api, formatDate } from "@/lib/api";
import { apiProblem, NOTHING_CHANGED } from "@/components/ApiProblem";
import { chipClass } from "@/lib/terms";
import { PlanControls } from "@/components/PlanControls";
import { EmailNoticesSwitch } from "@/components/EmailNoticesSwitch";

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
  const problem = apiProblem(meRes, { what: "your profile", note: NOTHING_CHANGED });
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
        <p>This page shows how you sign in and which plan this account is on.</p>
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
          <p className="card__why">Your name and email come from the account you sign in with, such as Google, so you change them there.</p>
        </div>

        <EmailNoticesSwitch on={me.email_notices ?? true} />

        <div className="card" data-testid="profile-plan">
          <h2>Your plan</h2>
          {sub?.status === "none" ? (
            <p data-testid="profile-no-plan">This account has no plan yet.</p>
          ) : (
            <ul className="rows">
              <li><span>Plan</span>{sub ? <strong>{sub.plan ? planName(sub.plan) : "None"}</strong> : unavailable}</li>
              <li><span>Status</span><span className={chipClass(statusTone)}>{statusLabel}</span></li>
              {next && <li><span>{next[0]}</span><strong>{next[1]}</strong></li>}
              {sub?.card_last4 && <li><span>Card</span><strong>Ending {sub.card_last4}</strong></li>}
            </ul>
          )}
          {sub?.status === "none" || sub?.status === "canceled" ? (
            <p><Link className="btn btn--primary btn--block" href="/billing">Choose a plan</Link></p>
          ) : null}
          {sub?.status === "past_due" ? (
            <p><Link className="btn btn--primary btn--block" href="/billing/payment-failed">See what happened</Link></p>
          ) : null}
          {sub && ["trialing", "active", "past_due"].includes(sub.status) ? (
            <p>
              <Link className="btn btn--quiet btn--block" data-testid="plan-change"
                href={`/billing/change?${new URLSearchParams({ back: `${base}/settings/profile` }).toString()}`}>
                Change plan
              </Link>
            </p>
          ) : null}
          {sub && ["trialing", "active", "past_due"].includes(sub.status) ? <PlanControls sub={sub} /> : null}
        </div>

        <p><a className="btn btn--quiet btn--block" href="/handler/sign-out" data-testid="profile-sign-out">Sign out</a></p>
        <p>
          <Link className="btn btn--quiet btn--block" href={`${base}/settings/delete`} data-testid="settings-delete">
            Delete my account
          </Link>
        </p>
        <p className="footnote">Deleting closes your account at once. After thirty days MyShopEdge erases your name and email. Until then you can sign in and cancel the deletion.</p>
      </div>
    </section>
  );
}
