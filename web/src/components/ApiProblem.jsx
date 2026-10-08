/**
 * The states a screen shows when the API does not give it figures.
 *
 * Every reading screen distinguishes four outcomes, because each tells the seller something
 * different: the service could not be reached, the session ended, the shop or record is not
 * theirs, or the service answered with an error. Rendering any of them as an empty list
 * would tell a seller their shop is empty, which is the one reading that is never true.
 *
 * The wording states only what is known. On 24 September two screens were found claiming
 * "your data is safe" when nothing had checked it, so no message here makes a claim about
 * the seller's data.
 */

import { redirect } from "next/navigation";

/**
 * The fallback note for a page that shows no figures, such as Disconnect or Profile and plan,
 * where "a wrong number" would mean nothing. A failed read changes nothing.
 */
export const NOTHING_CHANGED = "Nothing has changed. Please try again in a moment.";

/**
 * @param {import("@/lib/api").ApiResult} result
 * @param {{ what: string, notFound?: string, note?: string }} copy
 *   `what` names what failed to load, such as "your stock". `notFound` replaces the 404
 *   wording where the missing thing is a record rather than the shop. `note` replaces the
 *   fallback's line about wrong numbers on a page that shows none.
 * @returns {React.ReactElement | null}  Null when the result is usable.
 */
export function apiProblem(result, { what, notFound, note }) {
  if (result.unreachable) {
    return (
      <Problem
        title="MyShopEdge could not be reached."
        note={`MyShopEdge could not load ${what}. Please try again in a moment.`}
        retry
      />
    );
  }
  // S37 (A14): a session that ran out mid onboarding lands on its own screen, not an error.
  if (result.status === 401 && String(result.data?.type ?? "").endsWith("/token_expired")) {
    redirect("/signed-out?reason=expired");
  }
  // S36 (A14): the address belongs to an account made with a different sign-in method.
  if (result.status === 409 && String(result.data?.type ?? "").endsWith("/email_already_linked")) {
    redirect("/account/email-in-use");
  }
  if (result.status === 401) {
    return (
      <Problem
        title="Please sign in again."
        note="Your session has ended, or you have not signed in on this device yet."
        signIn
      />
    );
  }
  if (result.status === 403 && String(result.data?.type ?? "").endsWith("/account_closing")) {
    // A30.1: a closing account can do one thing, which is to cancel. Every screen that
    // meets the refusal sends the seller to the page that offers it.
    redirect("/account/closing");
  }
  // Until 8 October every other 403 read "That shop is not on your account.", including the
  // refusals that are about the account itself, which /me and every shop route can answer.
  const code = String(result.data?.code ?? "");
  if (result.status === 403 && code === "email_unverified") {
    return (
      <Problem
        title="Your email address is not verified yet."
        note="Verify it with the provider you sign in with, such as Google, then come back to this page."
      />
    );
  }
  if (result.status === 403 && code === "email_required") {
    return (
      <Problem
        title="Your sign-in has no email address."
        note="MyShopEdge needs a verified email address to set up your shop. Sign in with an account that has one."
        signIn
      />
    );
  }
  if (result.status === 403 && code === "account_suspended") {
    return (
      <Problem
        title="This account is suspended."
        note="Nothing in it has been deleted. Please contact MyShopEdge to find out why and what happens next."
      />
    );
  }
  if (result.status === 403) {
    return (
      <Problem
        title="That shop is not on your account."
        note="Check the address, or pick a shop from your connections."
      />
    );
  }
  if (result.status === 404) {
    return (
      <Problem
        title={notFound ?? "That shop is not on your account."}
        note="Check the address and try again."
      />
    );
  }
  // The provider has signed the seller in before the service has their email (auth.py). It
  // clears on its own, so it is not reported as a failure.
  if (result.status === 503 && code === "identity_syncing") {
    return (
      <Problem
        title="MyShopEdge is still setting up your account."
        note="Please try again in a moment."
        retry
      />
    );
  }
  if (!result.ok || !result.data) {
    return (
      <Problem
        title={`${what.charAt(0).toUpperCase()}${what.slice(1)} could not be loaded.`}
        note={note ?? "We show nothing rather than risk showing a wrong number. Please try again in a moment."}
        retry
      />
    );
  }
  return null;
}

/** @param {{ title: string, note: string, retry?: boolean, signIn?: boolean, startAgain?: boolean }} props */
export function Problem({ title, note, retry, signIn, startAgain }) {
  return (
    <section className="state">
      <h1>{title}</h1>
      <p>{note}</p>
      {retry && (
        <p>
          <a className="btn btn--quiet" href="">
            Try again
          </a>
        </p>
      )}
      {startAgain && (
        <p>
          <a className="btn btn--primary" href="/shops">
            Start again
          </a>
        </p>
      )}
      {signIn && (
        <p>
          <a className="btn btn--primary" href="/start">
            Sign in
          </a>
        </p>
      )}
    </section>
  );
}
