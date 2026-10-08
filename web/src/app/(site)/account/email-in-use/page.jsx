/**
 * S36 That email is already in use (A14). Built 29 September 2026.
 *
 * `create_account` refuses a second account for an address already held under a different
 * sign-in method, and the service answers 409 `email_already_linked`. Every screen that meets
 * that answer sends the seller here. A14 rules that the method is named only where the
 * provider says which it was. Nothing tells the service that, so no method is named.
 */

export const metadata = { title: "That email is already in use" };

export default function EmailInUsePage() {
  return (
    <section className="billing" data-testid="email-in-use">
      <h1>That email is already in use</h1>
      <p>Your email address already belongs to a MyShopEdge account that was created with a different way of signing in.</p>
      <p>Sign out, then sign in the way you did the first time. Your shop and figures are on that account.</p>
      <p><a className="btn btn--primary btn--block" href="/handler/sign-out">Sign out and sign in again</a></p>
    </section>
  );
}
