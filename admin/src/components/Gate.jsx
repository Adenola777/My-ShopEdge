/**
 * What a page shows when its view did not load. Nothing on these states names the reason
 * the service refused, because the service itself does not say (A34.3).
 */

import Link from "next/link";

/** @param {{ loaded: import("@/lib/load").Loaded }} props */
export function Gate({ loaded }) {
  if (loaded.state === "unconfigured") {
    return <p className="note">Sign-in is not configured on this deployment, because NEXT_PUBLIC_STACK_PROJECT_ID is not set.</p>;
  }
  if (loaded.state === "signed_out") {
    return (
      <div className="note">
        <p>Sign in with the admin email to continue.</p>
        <p><Link className="btn" href="/handler/sign-in">Sign in</Link></p>
      </div>
    );
  }
  if (loaded.state === "refused") {
    return (
      <div className="note">
        <p>This sign-in cannot open the admin pages.</p>
        <p>The service admits only the addresses on its allow-list, and only once the sign-in provider has verified the address.</p>
        <p><Link className="btn btn--quiet" href="/handler/sign-out">Sign out</Link></p>
      </div>
    );
  }
  if (loaded.state === "unreachable") {
    return <p className="note">The service could not be reached, so nothing is shown. Try again in a moment.</p>;
  }
  if (loaded.state === "error") {
    return <p className="note">The service answered {loaded.status}. {loaded.detail}</p>;
  }
  return null;
}
