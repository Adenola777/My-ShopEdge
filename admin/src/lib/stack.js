/**
 * The admin site's Stack Auth client (A34.6). It signs in through the same Stack project as
 * the seller app, which is why the admin site's address must be on Neon Auth's trusted
 * domains. What `@stackframe/stack` 2.8.108 does with these options was read from the
 * package for the seller app on 24 September 2026 (`web/src/lib/stack.js`), and the same
 * version is pinned here.
 *
 * Being signed in does not make anybody an admin. The service decides that, from
 * `ADMIN_EMAILS` and the provider's record of a verified email (A34.3), and answers 404 to
 * everyone else. This site only carries the token.
 */

import { StackClientApp } from "@stackframe/stack";

export const STACK_CONFIGURED = Boolean(process.env.NEXT_PUBLIC_STACK_PROJECT_ID);

export const stackApp = STACK_CONFIGURED
  ? new StackClientApp({
      tokenStore: "nextjs-cookie",
      urls: { afterSignIn: "/", afterSignUp: "/", afterSignOut: "/", home: "/" },
    })
  : null;

/** @returns {Promise<string | null>} */
export async function authorizationHeader() {
  if (!stackApp) return null;
  try {
    const { accessToken } = await stackApp.getAuthJson();
    return accessToken ? `Bearer ${accessToken}` : null;
  } catch {
    return null;
  }
}

/** @returns {Promise<import("@stackframe/stack").CurrentUser | null>} */
export async function currentUser() {
  if (!stackApp) return null;
  try {
    return await stackApp.getUser();
  } catch {
    return null;
  }
}
