/**
 * S38 Payment did not go through (A14). Built 29 September 2026 on getSubscription.
 *
 * A14 rules that the seller keeps read access to their figures while the account is past
 * due, and every screen does, because nothing in the service refuses a past-due account.
 * Two things A14 lists are not stated, because nothing holds them: when Stripe will try the
 * card again, and how long the data is kept if the payment never goes through. Changing the
 * card is not built, because the contract has no operation for it, so the screen says so
 * rather than offering a button that does nothing, and it names no contact route, because
 * none exists.
 */

import Link from "next/link";
import { redirect } from "next/navigation";
import { api, formatDate } from "@/lib/api";
import { STACK_CONFIGURED, currentUser } from "@/lib/stack";

export const metadata = { title: "Payment did not go through" };
export const dynamic = "force-dynamic";

export default async function PaymentFailedPage() {
  if (STACK_CONFIGURED && !(await currentUser())) redirect("/start");
  const sub = await api("/billing/subscription", { cache: "no-store" });
  if (sub.status === 401) redirect("/start");
  if (!sub.ok || sub.data?.status !== "past_due") redirect("/shops");
  return (
    <main className="billing" data-testid="payment-failed">
      <h1>Your payment did not go through</h1>
      <p>Your bank did not accept the last payment for your {sub.data.plan ?? ""} plan. This is often a bank being cautious rather than a problem with your account.</p>
      {sub.data.current_period_end && <p>The period it was for ends on {formatDate(sub.data.current_period_end)}.</p>}
      <p>Your figures stay open to you while this is sorted.</p>
      <p className="note">To update your card, email <a href="mailto:info@inspirecraftglobal.com">info@inspirecraftglobal.com</a> and we will send you a secure link.</p>
      <p><Link className="btn btn--primary btn--block" href="/shops">Go to your shop</Link></p>
    </main>
  );
}
