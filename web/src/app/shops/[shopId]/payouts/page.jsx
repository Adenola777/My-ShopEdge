/**
 * Reconcile, opening on Payouts (A36 step 5, from the owner's brief, section 12, approved
 * 10 October 2026). Every statement TikTok has issued, newest first, from `listSettlements`,
 * with the payout status the service works out (`reconcile_status`) and the difference the
 * orders behind it leave. Selecting a payout opens Explain this payout.
 *
 * TikTok pays each statement once, so a payout here is a statement and its payment, and the
 * linked statement is that statement. Orders TikTok has not yet put on a statement are shown
 * above the list as Awaiting settlement, from `getExpectedPayouts`, which asks TikTok when
 * the page opens. If TikTok does not answer, that part says so and the list is unaffected.
 *
 * What TikTok has paid and what it still owes, all time, sits at the top. It was the Shop
 * Money card on Overview until this step, and moved here so Overview carries one answer.
 *
 * On Pro, since 10 October 2026, the statements that need review come first, from
 * getPayoutReview: those whose orders do not add up to them, the largest difference first.
 * Other plans see the list alone, because getPayoutReview answers them with a 403.
 */

import Link from "next/link";
import { fetchShop, formatDate } from "@/lib/api";
import { apiProblem } from "@/components/ApiProblem";
import { Figure } from "@/components/Figure";
import { AWAITING, PAYOUT_STATUS, chipClass } from "@/lib/terms";

export const metadata = { title: "Reconcile" };

/** @typedef {import("@/lib/api-types").components["schemas"]["TodayView"]["shop_money"]} ShopMoney */

/** @param {{ status: string | null | undefined }} props */
function StatusChip({ status }) {
  const [word, tone] = PAYOUT_STATUS[status ?? ""] ?? ["Status not known", "quiet"];
  return <span className={chipClass(tone)} data-testid="payout-status">{word}</span>;
}

/** @param {{ params: Promise<{ shopId: string }>, searchParams: Promise<Record<string, string>> }} props */
export default async function PayoutsPage({ params, searchParams }) {
  const { shopId } = await params;
  const { cursor } = await searchParams;
  const [result, review, today, expected] = await Promise.all([
    fetchShop(shopId, "/settlements", { cursor, limit: "50" }),
    cursor ? Promise.resolve(null) : fetchShop(shopId, "/payout-review"),
    cursor ? Promise.resolve(null) : fetchShop(shopId, "/today"),
    cursor ? Promise.resolve(null) : fetchShop(shopId, "/payouts/expected"),
  ]);
  const problem = apiProblem(result, { what: "your payouts" });
  if (problem) return problem;

  /** @type {import("@/lib/api-types").components["schemas"]["Settlement"][]} */
  const rows = result.data.settlements ?? [];
  const next = result.data.next_cursor;
  /** @type {ShopMoney | null} */
  const sm = today?.ok ? today.data?.shop_money ?? null : null;

  return (
    <section data-testid="payouts-screen">
      <header className="page-head">
        <h1>Reconcile</h1>
        <p>Match settlements and payouts, then inspect every deduction behind them.</p>
      </header>

      <div className="stack">
        {sm ? <PaidAndOwed sm={sm} /> : null}

        {review?.ok && review.data ? <NeedsReview data={review.data} shopId={shopId} /> : null}

        {expected ? <AwaitingSettlement result={expected} /> : null}

        <h2>Payouts</h2>
        {rows.length === 0 ? (
          <div className="card"><p className="muted">TikTok has not issued a statement for this shop yet.</p></div>
        ) : (
          rows.map((s) => (
            <Link key={s.id} href={`/shops/${shopId}/payouts/${s.id}`} className="card rowlink" data-testid="payout-row">
              <ul className="rows">
                <li>
                  <span>{s.paid_at ? `Paid ${formatDate(s.paid_at)}` : "Not paid yet"}</span>
                  <StatusChip status={s.reconcile_status} />
                </li>
                <li className="rows__total"><span>Payout amount</span><Figure amount={s.payable_amount} /></li>
                <li>
                  <span>Linked statement</span>
                  <span>{formatDate(s.statement_time)}, <Figure amount={s.statement_amount} /></span>
                </li>
                <li>
                  <span>Difference</span>
                  <Figure amount={s.difference} reason="The difference was not worked out for this payout." />
                </li>
              </ul>
              <p className="card__foot">Explain this payout</p>
            </Link>
          ))
        )}
      </div>

      {next && (
        <p><Link className="btn btn--quiet btn--block" href={`/shops/${shopId}/payouts?${new URLSearchParams({ cursor: next })}`}>Older payouts</Link></p>
      )}
    </section>
  );
}

/**
 * What TikTok has paid and what it still owes, from Today's `shop_money`, which the service
 * computes. It was the Shop Money card on Overview.
 *
 * @param {{ sm: ShopMoney }} props
 */
function PaidAndOwed({ sm }) {
  const awaiting = sm.awaiting_breakdown ?? [];
  return (
    <div className="card" data-testid="paid-and-owed">
      <h2>Paid and still to come</h2>
      <p className="card__why">
        This covers every sale MyShopEdge holds for this shop: what TikTok has paid you, and what
        it still owes you.
      </p>
      <ul className="rows">
        <li><span>Net proceeds, all time</span><Figure amount={sm.generated} /></li>
        {sm.return_postage && sm.return_postage.amount_minor !== 0 && (
          <li><span>Return shipping TikTok deducted</span><Figure amount={sm.return_postage} /></li>
        )}
        <li><span>Paid out</span><Figure amount={sm.paid_out} /></li>
        <li><span>Awaiting settlement</span><Figure amount={sm.awaiting} /></li>
      </ul>
      <p className="rows__sub">
        Paid out and awaiting settlement together make up net proceeds less the return shipping
        TikTok deducted.
      </p>
      {awaiting.length > 0 && (
        <details className="disclose">
          <summary>What is awaiting settlement</summary>
          <ul className="rows">
            {awaiting.map((a) => (
              <li key={a.status} className="rows__sub">
                <span>
                  {AWAITING[a.status] ?? "Awaiting settlement"}, {a.orders} {a.orders === 1 ? "order" : "orders"}
                </span>
                <Figure amount={a.amount} />
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

/**
 * Orders TikTok has not yet put on a statement, by the week TikTok expects to pay them. This is
 * normal timing, so the status is Awaiting settlement and never a fault.
 *
 * @param {{ result: import("@/lib/api").ApiResult }} props
 */
function AwaitingSettlement({ result }) {
  if (!result.ok || !result.data) {
    return (
      <div className="card" data-testid="awaiting-settlement">
        <h2>Awaiting settlement</h2>
        <p className="card__why">
          TikTok did not answer just now, so the payouts it still expects to make are not shown.
          The payouts below are unaffected.
        </p>
      </div>
    );
  }
  /** @type {import("@/lib/api-types").components["schemas"]["ExpectedPayouts"]} */
  const p = result.data;
  if (p.weeks.length === 0) return null;
  return (
    <div className="card" data-testid="awaiting-settlement">
      <h2>Awaiting settlement</h2>
      <p className="card__why">
        TikTok has not put these orders on a statement yet. This is normal timing. Each amount is
        TikTok&apos;s own estimate and can change before TikTok settles.
      </p>
      <ul className="rows">
        {p.weeks.map((w) => (
          <li key={w.week_starting}>
            <span>
              Expected week of {formatDate(w.week_starting)}
              {w.orders > 0 ? `, ${w.orders} ${w.orders === 1 ? "order" : "orders"}` : ""}{" "}
              <StatusChip status="awaiting_settlement" />
            </span>
            <Figure amount={w.amount} />
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Pro's review list. Each statement links to its own page, where the difference is explained.
 *
 * @param {{ data: { items: { settlement: import("@/lib/api-types").components["schemas"]["Settlement"], orders_settled: number, unexplained: import("@/lib/api-types").components["schemas"]["Money"] }[], total_needing_review: number }, shopId: string }} props
 */
function NeedsReview({ data, shopId }) {
  if (data.total_needing_review === 0) {
    return (
      <div className="card" data-testid="payout-review-clear">
        <h2>Needs review</h2>
        <p className="muted">Every statement adds up to the orders behind it.</p>
      </div>
    );
  }
  return (
    <div className="card" data-testid="payout-review">
      <h2>Needs review</h2>
      <p className="card__why">
        {data.total_needing_review === 1
          ? "One statement does not add up to the orders behind it."
          : `${data.total_needing_review} statements do not add up to the orders behind them. The largest difference is first.`}
      </p>
      <ul className="rows">
        {data.items.map((i) => (
          <li key={i.settlement.id}>
            <Link className="rowlink rowlink--quiet" href={`/shops/${shopId}/payouts/${i.settlement.id}`}>
              {formatDate(i.settlement.statement_time)}
            </Link>
            <Figure amount={{ ...i.unexplained, amount_minor: Math.abs(i.unexplained.amount_minor) }} unsigned />
          </li>
        ))}
      </ul>
    </div>
  );
}
