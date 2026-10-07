/**
 * The reviewer credential login, added 7 October 2026 for the TikTok Shop Go Live review.
 *
 * TikTok's reviewers sign in with an email and a password, and the product's own sign-in is
 * Google only. This route accepts one fixed email and password, set in the environment, and
 * mints a short-lived ES256 token the service trusts on the demo deployment alone (see
 * `service/app/auth.py`, the reviewer path). The token carries the demo account's subject,
 * so the reviewer lands on the demo shop with its sample data.
 *
 * It is off unless all four variables are set, which is the demo service and nowhere else.
 * Production does not set them, so this answers 404 there and nothing changes.
 *
 *   REVIEWER_JWT_PRIVATE_JWK  the ES256 private key, as a JWK (its public half is on the service)
 *   REVIEWER_EMAIL            the one email that is accepted
 *   REVIEWER_PASSWORD         the one password that is accepted
 *   REVIEWER_SUBJECT          the demo account's subject (DEMO_ACCOUNT_SUBJECT) is used if unset
 */

import crypto from "node:crypto";
import { SignJWT, importJWK } from "jose";
import { cookies } from "next/headers";

export const dynamic = "force-dynamic";

/** Constant-time string compare that does not leak which, or how long, differs. */
function sameString(/** @type {string} */ a, /** @type {string} */ b) {
  const x = Buffer.from(String(a));
  const y = Buffer.from(String(b));
  // Compare a fixed-size digest so unequal lengths do not short-circuit or throw.
  const dx = crypto.createHash("sha256").update(x).digest();
  const dy = crypto.createHash("sha256").update(y).digest();
  return crypto.timingSafeEqual(dx, dy);
}

export async function POST(/** @type {Request} */ request) {
  const privRaw = process.env.REVIEWER_JWT_PRIVATE_JWK;
  const email = process.env.REVIEWER_EMAIL;
  const password = process.env.REVIEWER_PASSWORD;
  const subject = process.env.REVIEWER_SUBJECT || process.env.DEMO_ACCOUNT_SUBJECT;
  if (!privRaw || !email || !password || !subject) {
    return Response.json({ error: "not_enabled" }, { status: 404 });
  }

  /** @type {{ email?: string, password?: string }} */
  let body = {};
  try { body = await request.json(); } catch { body = {}; }
  const givenEmail = String(body.email ?? "").trim().toLowerCase();
  const givenPassword = String(body.password ?? "");
  if (!sameString(givenEmail, email.trim().toLowerCase()) || !sameString(givenPassword, password)) {
    return Response.json({ error: "invalid_credentials" }, { status: 401 });
  }

  let jwk;
  try { jwk = JSON.parse(privRaw); } catch {
    return Response.json({ error: "misconfigured" }, { status: 500 });
  }
  const key = await importJWK(jwk, "ES256");
  const now = Math.floor(Date.now() / 1000);
  const token = await new SignJWT({ email, emailVerified: true })
    .setProtectedHeader({ alg: "ES256", kid: jwk.kid ?? "reviewer" })
    .setIssuer(process.env.REVIEWER_ISS || "mse-reviewer")
    .setAudience(process.env.REVIEWER_AUD || "mse-reviewer")
    .setSubject(subject)
    .setIssuedAt(now)
    .setExpirationTime(now + 60 * 60 * 12)
    .sign(key);

  const jar = await cookies();
  // Readable by the browser as well as the server, so a client-side request can carry it in
  // the Authorization header the same way a Stack session is carried. It grants access to
  // the demo account's sample data only, and it expires in twelve hours.
  jar.set("mse_reviewer", token, {
    httpOnly: false, secure: true, sameSite: "lax", path: "/", maxAge: 60 * 60 * 12,
  });
  return Response.json({ ok: true });
}
