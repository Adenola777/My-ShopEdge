/**
 * Where a seller whose account is closing lands (A30.1). Built 28 September 2026.
 *
 * Every operation except getMe and cancelAccountDeletion refuses a closing account with
 * `account_closing`, and every shop screen sends that refusal here (`apiProblem`). The page
 * states the date the account is erased and offers the one thing A30.1 allows, which is to
 * keep it. A seller whose account is not closing is sent on to their shop.
 */

import { redirect } from "next/navigation";
import { api, formatDate } from "@/lib/api";
import { STACK_CONFIGURED, currentUser } from "@/lib/stack";
import { CancelDeletion } from "@/components/AccountDeletion";

export const metadata = { title: "Your account is closing" };

export const dynamic = "force-dynamic";

export default async function ClosingPage() {
  if (STACK_CONFIGURED && !(await currentUser())) redirect("/start");
  const me = await api("/me", { cache: "no-store" });
  if (me.status === 401) redirect("/start");
  if (!me.ok || !me.data) {
    return (
      <main className="billing">
        <h1>MyShopEdge could not be reached.</h1>
        <p>Nothing has changed on your account. Try again in a moment.</p>
      </main>
    );
  }
  const when = me.data.deletion_scheduled_at;
  if (me.data.status !== "deleted" || !when) redirect("/shops");

  return (
    <main className="billing" data-testid="closing-screen">
      <h1>Your account is closing</h1>
      <p>
        On {formatDate(when)} your name and email are erased, your TikTok sign-in details
        are erased, and every file you uploaded or exported is deleted. Your financial records
        stay, attached to no person.
      </p>
      <p>Until then you can keep your account. Your shop stays disconnected, so you connect it again afterwards.</p>
      <CancelDeletion />
      <p><a className="btn btn--quiet btn--block" href="/handler/sign-out">Sign out</a></p>
    </main>
  );
}
