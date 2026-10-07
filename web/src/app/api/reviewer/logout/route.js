/**
 * Clears the reviewer credential cookie. Added 7 October 2026 with the reviewer login.
 */

import { cookies } from "next/headers";

export const dynamic = "force-dynamic";

export async function POST() {
  const jar = await cookies();
  jar.set("mse_reviewer", "", { httpOnly: false, secure: true, sameSite: "lax", path: "/", maxAge: 0 });
  return Response.json({ ok: true });
}
