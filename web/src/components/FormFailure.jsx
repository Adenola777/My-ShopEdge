/**
 * What a settings or data form says when its request fails. Written 9 October 2026 for the
 * copy audit of 8 October (Area C, "Every client form").
 *
 * Since 8 October the service answers every failure with a `detail` that is a sentence for
 * the seller (`service/app/problems.py`), including validation, so the detail is shown as it
 * comes. Two answers need more than their sentence, and this file adds it.
 *
 * - A 401 says "Sign in again" with nowhere to click, so the form adds a Sign in link to
 *   /start, the address the read screens' own sign-in button uses (`ApiProblem.jsx`).
 * - A 500 `internal_error` says only "Something went wrong at our end." An unhandled error
 *   can come before or after a change is stored, so the form does not claim that nothing was
 *   saved. It says how to find out.
 *
 * @typedef {{ message: string, signIn: boolean }} Failure
 */

/**
 * @param {import("@/lib/api").ApiResult} r
 * @param {{ fallback: string, unreachable: string }} copy
 *   `fallback` is shown when the answer carries no sentence. `unreachable` is shown when the
 *   service could not be reached, and says what that means for this form.
 * @returns {Failure}
 */
export function formFailure(r, { fallback, unreachable }) {
  if (r.unreachable) return { message: unreachable, signIn: false };
  const detail = typeof r.data?.detail === "string" && r.data.detail.trim() !== "" ? r.data.detail : null;
  if (r.status === 401) {
    return { message: "Your session has ended, so this was not sent. Sign in again, then repeat it.", signIn: true };
  }
  if (r.status >= 500 && (r.data?.code === "internal_error" || !detail)) {
    return {
      message: "Something went wrong at MyShopEdge's end. Reload the page to see whether the change was made, and try again if it was not.",
      signIn: false,
    };
  }
  return { message: detail ?? fallback, signIn: false };
}

/** @param {{ failure: Failure | null, testId?: string }} props */
export function FormError({ failure, testId }) {
  if (!failure) return null;
  return (
    <p className="form-error" role="alert" data-testid={testId}>
      {failure.message}
      {failure.signIn && <> <a href="/start">Sign in</a></>}
    </p>
  );
}
