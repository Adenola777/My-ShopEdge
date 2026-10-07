"use client";

/**
 * The reviewer sign-in page, added 7 October 2026 for the TikTok Shop Go Live review.
 *
 * It takes the one email and password set in the environment, posts them to
 * /api/reviewer/login, and on success sends the reviewer to the shop. It works only on the
 * demo deployment, where the reviewer variables are set; elsewhere the login route answers
 * 404 and this page says sign-in is not available here.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function ReviewerSignIn() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));

  /** @param {React.FormEvent} e */
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    let res;
    try {
      res = await fetch("/api/reviewer/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
    } catch {
      setBusy(false);
      setError("We could not reach the sign-in service. Try again in a moment.");
      return;
    }
    if (res.ok) {
      router.push("/shops");
      router.refresh();
      return;
    }
    setBusy(false);
    if (res.status === 404) setError("Email sign-in is not available on this site.");
    else if (res.status === 401) setError("That email or password was not recognised.");
    else setError("Sign-in did not work just now. Try again in a moment.");
  }

  return (
    <section className="start">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="start__logo" src="/brand/mse-logo-horizontal.svg" alt="MyShopEdge, Know Your Numbers" width={240} height={89} />
      <h1>Sign in</h1>
      <p className="muted">Enter the email and password you were given to review MyShopEdge.</p>
      <form className="stack" style={{ maxWidth: 360, margin: "0 auto", textAlign: "left" }} onSubmit={submit}>
        <label htmlFor="rev-email">Email</label>
        <input id="rev-email" type="email" autoComplete="username" required value={email}
               onChange={(e) => setEmail(e.target.value)} disabled={busy} data-testid="reviewer-email" />
        <label htmlFor="rev-password">Password</label>
        <input id="rev-password" type="password" autoComplete="current-password" required value={password}
               onChange={(e) => setPassword(e.target.value)} disabled={busy} data-testid="reviewer-password" />
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="btn btn--primary btn--block" type="submit" disabled={busy} data-testid="reviewer-submit">
          {busy ? "Signing in" : "Sign in"}
        </button>
      </form>
    </section>
  );
}
