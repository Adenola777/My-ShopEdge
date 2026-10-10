/**
 * The one way the admin site talks to the service. A trimmed copy of `web/src/lib/api.js`:
 * the bearer token is read on whichever side the call is made, and a network failure becomes
 * a result rather than an exception.
 *
 * @typedef {import("./api-types").components["schemas"]} Schemas
 */

import { authorizationHeader } from "./stack";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/v1";

/**
 * @typedef {Object} ApiResult
 * @property {boolean} ok
 * @property {number} status  0 when the request never reached the service.
 * @property {any} data
 */

/**
 * @param {string} path
 * @param {RequestInit} [init]
 * @returns {Promise<ApiResult>}
 */
export async function api(path, init = {}) {
  /** @type {Record<string, string>} */
  const headers = { "content-type": "application/json" };
  const authorization = await authorizationHeader();
  if (authorization) headers.Authorization = authorization;
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      cache: "no-store",
      ...init,
      headers,
      signal: AbortSignal.timeout ? AbortSignal.timeout(30000) : undefined,
    });
  } catch {
    return { ok: false, status: 0, data: null };
  }
  const data = await response.json().catch(() => null);
  return { ok: response.ok, status: response.status, data };
}
