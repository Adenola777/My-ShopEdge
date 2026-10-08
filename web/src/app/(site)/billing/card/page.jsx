/**
 * Change card. Reached from S41 Profile and plan while the plan is live. Added 8 October 2026.
 */

import Link from "next/link";
import { redirect } from "next/navigation";
import { api } from "@/lib/api";
import { STACK_CONFIGURED, currentUser } from "@/lib/stack";

import { CardChangeForm } from "./CardChangeForm";

export const metadata = { title: "Change card" };

export const dynamic = "force-dynamic";

const LIVE = ["trialing", "active", "past_due"];

export default async function CardPage() {
  if (STACK_CONFIGURED && !(await currentUser())) redirect("/start");
  const [subRes, shopsRes] = await Promise.all([
    api("/billing/subscription", { cache: "no-store" }),
    api("/shops", { cache: "no-store" }),
  ]);
  if (subRes.status === 401) redirect("/start");
  const firstShop = shopsRes.ok ? (shopsRes.data?.shops ?? [])[0] : null;
  const back = firstShop ? `/shops/${firstShop.id}/settings/profile` : "/shops";

  if (!subRes.ok || !LIVE.includes(subRes.data?.status)) {
    return (
      <main className="billing">
        <h1>There is no plan to change the card on.</h1>
        <p>A card can be changed while a plan or a free trial is running.</p>
        <Link className="btn btn--primary" href={back}>Back</Link>
      </main>
    );
  }

  return (
    <main className="billing">
      <CardChangeForm back={back} />
    </main>
  );
}
