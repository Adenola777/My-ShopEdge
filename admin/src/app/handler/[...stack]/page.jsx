/**
 * Stack Auth's own pages for the admin site: sign in, the OAuth return and sign out. The
 * Suspense boundary is the one `web/src/app/(site)/handler/[...stack]/page.jsx` explains:
 * the sign-out page suspends while it renders on the server.
 */

import { Suspense } from "react";
import { StackHandler } from "@stackframe/stack";
import { STACK_CONFIGURED } from "@/lib/stack";

export default function Handler() {
  if (!STACK_CONFIGURED) {
    return <p className="note">Sign-in is not configured on this deployment.</p>;
  }
  return (
    <Suspense fallback={<p aria-live="polite">One moment.</p>}>
      <StackHandler fullPage />
    </Suspense>
  );
}
