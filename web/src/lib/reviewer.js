/**
 * Whether this deployment takes the reviewer sign-in (12 October 2026).
 *
 * TikTok rejected the Go Live review a second time with "Wrong e-mail or password", which is
 * Stack Auth's own message: the reviewers typed the test credentials into the Google sign-in
 * page, which has never held them, rather than into `/reviewer`. On a deployment where the
 * reviewer sign-in is configured, which is the demo branch alone, the front page, Get started
 * and Stack's sign-in and sign-up pages therefore all lead to `/reviewer`, so every way in
 * reaches the form that takes those credentials.
 *
 * Read on the server only. Production sets none of these variables, so there it is false and
 * nothing changes. `?google=1` on Stack's sign-in page still reaches Google sign-in.
 */
export const REVIEWER_ENABLED = Boolean(
  process.env.REVIEWER_EMAIL && process.env.REVIEWER_PASSWORD && process.env.REVIEWER_JWT_PRIVATE_JWK,
);
