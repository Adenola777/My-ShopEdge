/**
 * Reads one admin view for a server page and says which of five states the page is in.
 *
 * The service answers 404 to anybody who is not an admin, exactly as for a path that does
 * not exist (A34.3), so a 404 on a list view is read as "this sign-in is not an admin". The
 * page says so plainly and shows nothing else.
 */

import { api } from "./api";
import { STACK_CONFIGURED, currentUser } from "./stack";

/**
 * @typedef {{ state: "ok", data: any }
 *   | { state: "signed_out" | "refused" | "unreachable" | "unconfigured" }
 *   | { state: "error", status: number, detail: string }} Loaded
 */

/** @param {string} path @returns {Promise<Loaded>} */
export async function load(path) {
  if (!STACK_CONFIGURED) return { state: "unconfigured" };
  if (!(await currentUser())) return { state: "signed_out" };
  const r = await api(path);
  if (r.status === 0) return { state: "unreachable" };
  if (r.status === 404) return { state: "refused" };
  if (!r.ok) return { state: "error", status: r.status, detail: r.data?.detail ?? "" };
  return { state: "ok", data: r.data };
}
