/**
 * S34. Payment confirmed.
 *
 * Where a seller lands after their bank takes them away for a 3D Secure challenge.
 *
 * S33 confirms the card in place where the bank allows it, using redirect "if_required".
 * Where the bank insists on a redirect, the seller leaves the site and comes back here.
 * Until A14 this route did not exist, so that seller reached a 404 with their card already
 * verified and no way to know it had worked.
 *
 * Stripe appends setup_intent and redirect_status to the return URL. The status in the URL
 * is a hint for what to show first and nothing more. It arrives from the browser, so it is
 * never trusted as the record of what happened: the subscription state comes from the API.
 *
 * The reminder this page promises is Stripe's own trial ending email, which Stripe's
 * documentation says goes seven days before a trial ends, or at once for a trial shorter
 * than seven days. The service sends no email of its own. The promise holds only while
 * "Send a reminder email 7 days before a free trial ends" is on in the live account's
 * Billing settings, which the owner turns on (ruled 8 October 2026). Stripe sends no such
 * email in a sandbox.
 */

import Link from "next/link";
import { redirect } from "next/navigation";
import { STACK_CONFIGURED, currentUser } from "@/lib/stack";
import { api } from "@/lib/api";

export const metadata = { title: "Card confirmed" };

/**
 * @param {{ searchParams: Promise<Record<string, string | undefined>> }} props
 */
export default async function ConfirmedPage({ searchParams }) {
  // A signed-out visitor has nothing to confirm (found 28 September, walking the journey).
  if (STACK_CONFIGURED && !(await currentUser())) redirect("/start");
  const params = await searchParams;
  const hint = params.redirect_status;

  const { ok, data } = await api("/billing/subscription", { cache: "no-store" });
  const status = ok && data ? data.status : null;

  if (status === "trialing" || status === "active") {
    const firstPayment = data.trial_ends_at
      ? new Date(data.trial_ends_at).toLocaleDateString("en-GB", {
          day: "numeric",
          month: "long",
        })
      : null;
    return (
      <section className="confirmed">
        <h1>Your card is confirmed and your trial has started.</h1>
        {firstPayment ? (
          <p>
            We take nothing until {firstPayment}. We will email you seven days before that.
          </p>
        ) : (
          <p>We will email you seven days before the first payment.</p>
        )}
        <Link className="btn btn--primary" href="/">
          Go to your shop
        </Link>
      </section>
    );
  }

  if (hint === "failed" || status === "past_due") {
    return (
      <section className="confirmed">
        <h1>Your bank did not confirm the card.</h1>
        <p>
          Nothing has been charged. Banks sometimes decline a first check, and trying again
          or using another card normally resolves it.
        </p>
        {status === "past_due" ? (
          <Link className="btn btn--primary" href="/billing/payment-failed">
            See what to do next
          </Link>
        ) : (
          <Link className="btn btn--primary" href="/billing">
            Try the card again
          </Link>
        )}
      </section>
    );
  }

  // Stripe sends redirect_status=processing while the bank has not yet answered. The
  // subscription then still reads as none, so without this state the seller was told there was
  // nothing waiting (copy audit of 8 October 2026).
  if (hint === "processing" && (status === "none" || status === null)) {
    return (
      <section className="confirmed" data-testid="confirmed-processing">
        <h1>Your bank is still confirming the card.</h1>
        <p>
          Nothing has been charged. Reload this page in a minute to see whether the card was
          confirmed and your trial has started.
        </p>
        <a className="btn btn--primary" href="">Check again</a>
      </section>
    );
  }

  // The seller's plan is shown on Profile and plan, which lives under a shop. A seller with
  // no plan yet is sent to choose one instead.
  const noPlan = status === "none" || status === null;
  let planHref = "/billing";
  if (!noPlan) {
    const shops = await api("/shops", { cache: "no-store" });
    const first = shops.ok ? (shops.data?.shops ?? [])[0] : null;
    if (first) planHref = `/shops/${first.id}/settings/profile`;
  }

  // Reloaded later, or arrived with no setup in progress. Showing the real state is more
  // useful than an error about a page that was only ever a staging post.
  return (
    <section className="confirmed">
      <h1>There is nothing waiting to be confirmed.</h1>
      <p>
        {status === "none" || status === null
          ? "You have not started a trial yet."
          : status === "trialing" ? "Your free trial is running." : status === "active" ? "Your plan is active." : status === "past_due" ? "Your last payment did not go through." : status === "canceled" ? "Your plan has ended." : "Your plan is being set up."}
      </p>
      <Link className="btn btn--primary" href={planHref}>
        {noPlan ? "Choose a plan" : "See your plan"}
      </Link>
    </section>
  );
}
