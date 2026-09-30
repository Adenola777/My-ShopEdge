import { redirect } from "next/navigation";
import { STACK_CONFIGURED, currentUser } from "@/lib/stack";

/**
 * The product website, where a visitor who is not signed in starts. Until 30 September 2026
 * this address sent everyone to `/shops`, so a first visit to the app's own address showed
 * "Please sign in again" instead of the product.
 */
const LANDING_URL = "https://myshopedge.inspirecraftglobal.com";

export const dynamic = "force-dynamic";

/**
 * The home address has nothing of its own. A signed in seller's figures live under their
 * shop; anyone else is sent to the landing page, whose Get started leads to `/start`.
 * Where sign-in is not configured, as on a local copy, it goes to `/shops` as before.
 */
export default async function Home() {
  if (STACK_CONFIGURED && !(await currentUser())) redirect(LANDING_URL);
  redirect("/shops");
}
