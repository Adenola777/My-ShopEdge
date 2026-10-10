/**
 * Where a signed-in seller lands. `listShops` returns the shops on the account, and the MVP
 * allows one (CON-3), so a seller with one shop is sent to the step of A14.2 they have
 * reached (`nextStep`): First sync, the plan, a connection problem, or Today. Before
 * 24 September nothing gave a seller their shop id, so no shop screen could be reached
 * except by typing its address.
 */

import Link from "next/link";
import { redirect } from "next/navigation";
import { api } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { ConnectTikTok } from "@/components/ConnectTikTok";
import { nextStep } from "@/lib/onboarding";

export const metadata = { title: "Your shops" };

/**
 * `?all=1` shows the list even to a seller with one shop. "Your shops" in the top bar and in
 * Settings link there, because without it the link sent a one-shop seller straight back into
 * the shop and appeared to do nothing (copy audit of 8 October 2026).
 *
 * @param {{ searchParams: Promise<{ all?: string }> }} props
 */
export default async function ShopsPage({ searchParams }) {
  const { all } = await searchParams;
  const result = await api("/shops", { cache: "no-store" });
  const problem = apiProblem(result, { what: "your shops" });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["Shop"][]} */
  const shops = result.data.shops ?? [];
  const only = shops.length === 1 && !all ? shops[0] : undefined;
  if (only) {
    // Resume at the right step of A14.2 rather than always at Today (lib/onboarding.js).
    const [sub, tax, costs] = await Promise.all([
      api("/billing/subscription", { cache: "no-store" }),
      api("/tax-profile", { cache: "no-store" }),
      api(`/shops/${encodeURIComponent(only.id)}/costs`, { cache: "no-store" }),
    ]);
    // A plan without costs (Starter) answers 403, which reads as no costs entered.
    const noCostPlan = costs.status === 403 && costs.data?.code === "plan_upgrade_required";
    const setupUntouched = tax.ok && (costs.ok || noCostPlan) && !tax.data?.completed
      && !(costs.ok ? costs.data?.skus ?? [] : []).some((/** @type {any} */ s) => s.cost);
    redirect(nextStep(only, sub.ok ? sub.data?.status ?? null : null, { setupUntouched }));
  }

  if (shops.length === 0) {
    // S1 Connect TikTok Shop, from wireframe sheet 02. Two lines of the wireframe are left
    // out because nothing behind them exists: disconnecting from Settings (neither the
    // Settings screen nor disconnectShop is built), and the step dots of an onboarding flow
    // whose other steps are not built either. "Not kept" for buyer details rests on SYN-7 and
    // the schema's own header, which rule that buyer data is dropped before anything is
    // written.
    return (
      <section>
        <header className="page-head">
          <h1>Connect your TikTok Shop</h1>
          <p>MyShopEdge reads your shop and never changes anything in it.</p>
        </header>
        <div className="stack">
          <div className="card">
            <h2>What we read</h2>
            <p className="card__why">We read only what we need to work out what you earned.</p>
            <ul className="rows">
              <li><span>Orders and sales</span><strong>Read</strong></li>
              <li><span>Products and stock</span><strong>Read</strong></li>
              <li><span>Payments and fees</span><strong>Read</strong></li>
              <li><span>Returns and refunds</span><strong>Read</strong></li>
            </ul>
          </div>
          <div className="card">
            <h2>What we do not keep</h2>
            <p className="card__why">Your buyers&rsquo; details stay with TikTok.</p>
            <ul className="rows">
              <li><span>Buyer names and addresses</span><strong>Not kept</strong></li>
            </ul>
          </div>
          <ConnectTikTok />
        </div>
      </section>
    );
  }

  return (
    <section>
      <header className="page-head"><h1>Your shops</h1></header>
      <div className="card">
        <ul className="rows">
          {shops.map((s) => (
            <li key={s.id}>
              <Link href={`/shops/${s.id}/today`}>{s.shop_name ?? s.tiktok_shop_id}</Link>
              <span className="rows__sub">{s.region === "GB" ? "United Kingdom" : s.region}</span>
            </li>
          ))}
        </ul>
      </div>
      <p><Link href="/shops/connect">Connect another shop</Link></p>
    </section>
  );
}
