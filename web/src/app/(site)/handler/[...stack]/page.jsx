/**
 * Stack Auth's own pages: sign in, sign up, the OAuth return, sign out.
 *
 * A14 section 14.3 rules that the provider hosts sign-in (S19) and that we brand it rather
 * than rebuild it. `StackHandler` in 2.8.108 takes its app from `StackProvider` in the root
 * layout; the `app` and `routeProps` props are marked deprecated in its own types.
 *
 * The OAuth return lands on /handler/oauth-callback on this domain, which is why
 * `https://my-shop-edge.vercel.app` was added to Neon Auth's trusted domains on
 * 24 September 2026.
 *
 * The Suspense boundary is required. On 8 October 2026 /handler/sign-out answered 500 on
 * production with "suspendIfSsr() should be wrapped in a suspense boundary": the sign-out
 * page suspends while it renders on the server, and nothing above it caught that. The same
 * build answered 200 on /handler/sign-in, which does not suspend there.
 */

import { Suspense } from "react";
import { StackHandler } from "@stackframe/stack";
import { STACK_CONFIGURED } from "@/lib/stack";
import { Problem } from "@/components/ApiProblem";

/** The page title for each of Stack's routes that a seller sees. */
const TITLES = /** @type {Record<string, string>} */ ({
  "sign-in": "Sign in",
  "sign-up": "Create an account",
  "sign-out": "Sign out",
});

/** @param {{ params: Promise<{ stack?: string[] }> }} props */
export async function generateMetadata({ params }) {
  const { stack } = await params;
  return { title: TITLES[stack?.[0] ?? ""] ?? "Account" };
}

export default function Handler() {
  if (!STACK_CONFIGURED) {
    return (
      <Problem
        title="Sign-in is not working at the moment."
        note="Nothing on your account has changed. Try again in a few minutes."
        retry
      />
    );
  }
  return (
    <Suspense fallback={<p aria-live="polite">One moment.</p>}>
      <StackHandler fullPage />
    </Suspense>
  );
}
