/**
 * S37 Signed out (A14). Built 29 September 2026. One screen, two states: signed out on
 * purpose, and a session that expired, which the service reports as `token_expired`. Neither
 * loses onboarding progress, because `/shops` resumes a returning seller at the step reached.
 */

export const metadata = { title: "Signed out" };

/** @param {{ searchParams: Promise<{ reason?: string }> }} props */
export default async function SignedOutPage({ searchParams }) {
  const { reason } = await searchParams;
  const expired = reason === "expired";
  return (
    <section className="billing" data-testid={expired ? "session-expired" : "signed-out"}>
      <h1>{expired ? "Your session has ended" : "You are signed out"}</h1>
      <p>{expired
        ? "Sign in again to carry on. Nothing you set up has been lost."
        : "Sign in whenever you are ready. Your shop and figures are as you left them."}</p>
      <p><a className="btn btn--primary btn--block" href="/handler/sign-in">Sign in</a></p>
    </section>
  );
}
