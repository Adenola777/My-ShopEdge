/**
 * S17 Start. The first thing a seller sees, in our name and our words, before the provider.
 *
 * A14 section 14.3: the logo, the tagline, one sentence saying what happens next, and two
 * actions, "Create account and connect my shop" (named "Create an account" until 10 October 2026) and "Sign in", which both hand off to the identity provider.
 * No password field appears here, because we never receive one. The logo and the tagline
 * are the masthead the root layout already draws.
 *
 * A15 section 15.3 folds the old S18 wait into this screen. A seller who is already signed in
 * is sent straight to their shops, so the wait never needs a page of its own.
 *
 * A14 requires links to the privacy notice and the terms below the actions, and section 11 of
 * the Data Protection Document requires the privacy notice. Both pages, with the cookie policy,
 * were published on 10 October 2026 as static files in `public/legal/`, built from the owner's
 * drafts, so this app serves them at its own address.
 *
 * The three providers switched on in Neon Auth on 24 September 2026 are Google, GitHub and
 * Microsoft. Email and password sign-in is off. The provider's page shows whichever are on.
 */

import { redirect } from "next/navigation";
import { STACK_CONFIGURED, currentUser } from "@/lib/stack";
import { Problem } from "@/components/ApiProblem";

export const metadata = { title: "Start" };
export const dynamic = "force-dynamic";

export default async function StartPage() {
  if (!STACK_CONFIGURED) {
    return (
      <Problem
        title="Sign-in is not working at the moment."
        note="Nothing on your account has changed. Try again in a few minutes."
        retry
      />
    );
  }

  if (await currentUser()) redirect("/shops");

  return (
    <section className="start">
      {/* A7.7: the sign-in and sign-up screens carry the horizontal lockup with the tagline.
          A7.6 allows it from 180 px wide; it is drawn at 240. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="start__logo" src="/brand/mse-logo-horizontal.svg" alt="MyShopEdge, Know Your Numbers" width={240} height={89} />
      {/* The heading, body and first button follow the landing page, so a seller who clicks
          "Start your free 30-day trial" lands on the same words (owner's brief, 10 October 2026). */}
      <h1>Start seeing what you actually keep.</h1>
      <p className="muted">
        Create your MyShopEdge account, then connect your TikTok Shop to bring sales, fees,
        refunds and payouts into one clear picture. You sign in with Google, GitHub or
        Microsoft. Your 30-day free trial starts when you choose a plan after connecting.
      </p>
      <div className="stack" style={{ maxWidth: 360, margin: "0 auto" }}>
        <a className="btn btn--primary btn--block" href="/handler/sign-up">Create account and connect my shop</a>
        <a className="btn btn--quiet btn--block" href="/handler/sign-in">Sign in</a>
      </div>
      <p className="muted" style={{ fontSize: 14, marginTop: 20 }}>
        By creating an account you agree to the <a href="/legal/terms.html">Terms and Conditions</a>.
        The <a href="/legal/privacy.html">Privacy Policy</a> and the <a href="/legal/cookies.html">Cookie Policy</a> explain
        how we handle your data.
      </p>
    </section>
  );
}
