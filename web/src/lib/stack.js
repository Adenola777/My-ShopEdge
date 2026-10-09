/**
 * The one Stack Auth client this application holds.
 *
 * What was read, 24 September 2026, from `@stackframe/stack` 2.8.108 itself rather than from
 * its documentation:
 *
 * - `getDefaultProjectId` throws when neither `NEXT_PUBLIC_STACK_PROJECT_ID` nor
 *   `STACK_PROJECT_ID` is set. The project id is the only value it demands.
 * - `getDefaultPublishableClientKey` returns `NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY` and
 *   throws nothing when it is absent. Whether this project's Stack configuration requires one
 *   could not be read, because the container that wrote this cannot reach
 *   api.stack-auth.com. It is set on Vercel regardless.
 * - `STACK_SECRET_SERVER_KEY` is demanded only by `StackServerApp`. This application uses
 *   `StackClientApp` on both sides, so no Stack secret lives on Vercel.
 * - With `tokenStore: "nextjs-cookie"`, the client app reads the browser's cookies in the
 *   browser and the request's cookies through `next/headers` on the server. One object
 *   therefore serves server components and client components alike.
 * - `getAuthJson()` returns `accessToken` as the raw token string (`tokens.accessToken.token`).
 *   `getAuthorizationHeader()` does not: it returns `Bearer stackauth_<base64 JSON>`, which
 *   the service would refuse, because `auth.py` verifies a bare ES256 JWT.
 *
 * When the project id is not set, as in CI and in a local build, `stackApp` is null and
 * every page that needs a seller says that sign-in is not configured. Constructing the app
 * without a project id would throw at import and break the whole build.
 *
 * **Verified on 24 September 2026.** The owner signed in on the live site, the token passed
 * through this code, and the service accepted it and created the account.
 */

import { StackClientApp } from "@stackframe/stack";

export const STACK_CONFIGURED = Boolean(process.env.NEXT_PUBLIC_STACK_PROJECT_ID);

export const stackApp = STACK_CONFIGURED
  ? new StackClientApp({
      tokenStore: "nextjs-cookie",
      urls: {
        afterSignIn: "/shops",
        afterSignUp: "/shops",
        // S37 confirms a deliberate sign-out (copy audit of 8 October 2026). Until then a
        // seller who signed out landed on Start with no word that it had worked.
        afterSignOut: "/signed-out",
        home: "/",
      },
    })
  : null;

/**
 * The value for the Authorization header, or null when nobody is signed in.
 *
 * A failure to read the session is treated as signed out rather than thrown, so that a
 * screen shows its signed out state instead of a 500.
 *
 * @returns {Promise<string | null>}
 */
export async function authorizationHeader() {
  // The reviewer credential, when present, takes precedence over the provider session. It is
  // set only on the demo deployment (see app/api/reviewer/login), so this is inert in
  // production, where the cookie never exists.
  const reviewer = await reviewerToken();
  if (reviewer) return `Bearer ${reviewer}`;
  if (!stackApp) return null;
  try {
    const { accessToken } = await stackApp.getAuthJson();
    return accessToken ? `Bearer ${accessToken}` : null;
  } catch {
    return null;
  }
}

/**
 * The reviewer token from its cookie, read on whichever side the caller runs, or null. In
 * the browser it is read from `document.cookie`; on the server from the request's cookies.
 *
 * @returns {Promise<string | null>}
 */
export async function reviewerToken() {
  if (typeof document !== "undefined") {
    const m = document.cookie.match(/(?:^|;\s*)mse_reviewer=([^;]+)/);
    return m && m[1] ? decodeURIComponent(m[1]) : null;
  }
  try {
    const { cookies } = await import("next/headers");
    const jar = await cookies();
    return jar.get("mse_reviewer")?.value ?? null;
  } catch {
    return null;
  }
}

/**
 * The signed in user, or null.
 *
 * @returns {Promise<import("@stackframe/stack").CurrentUser | null>}
 */
export async function currentUser() {
  // A reviewer with the credential cookie counts as signed in, so the page guards admit
  // them. The real identity and the account come from the token the service verifies, not
  // from this stub, which exists only to pass `if (!(await currentUser())) redirect(...)`.
  if (await reviewerToken()) return /** @type {any} */ ({ id: "reviewer", isReviewer: true });
  if (!stackApp) return null;
  try {
    return await stackApp.getUser();
  } catch {
    return null;
  }
}
