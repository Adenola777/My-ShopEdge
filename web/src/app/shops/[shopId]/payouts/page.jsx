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
 *
 * Since 11 October 2026 (A36 item 6), a payout TikTok lists that no statement names is shown
 * as Unmatched above the list, from the first page's `unmatched`. Nothing is shown when every
 * payout has its statement.
 */

import { Pager } from "@/components/Pager";
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

  const unmatched = result.data.unmatched ?? [];

  // A37 phase 3, 11 October 2026: the Overview's pattern. What TikTok has paid and still owes
  // in one card of three figures, anything that needs a look, and then every payout as one row
  // of a single list, where each payout had been a card of its own.
  return (
    <section className="overview" data-testid="payouts-screen">
      <header className="page-head">
        <h1>Reconcile</h1>
        <p>Payouts matched to statements.</p>
      </header>

      {sm ? <PaidAndOwed sm={sm} /> : null}

      {review?.ok && review.data && review.data.total_needing_review > 0 ? <NeedsReview data={review.data} shopId={shopId} /> : null}

      {unmatched.length > 0 && <Unmatched payouts={unmatched} />}

      {expected ? <AwaitingSettlement result={expected} shopId={shopId} /> : null}

      <h2 className="overview__heading">Payouts</h2>
      <div className="card" data-testid="payouts-list">
        {rows.length === 0 ? (
          <p className="muted">No statement from TikTok yet.</p>
        ) : (
          <ul className="rows payouts">
            {rows.map((s) => {
              const off = s.difference && s.difference.amount_minor !== 0;
              return (
                <li key={s.id} data-testid="payout-row">
                  <Link className="payouts__row" href={`/shops/${shopId}/payouts/${s.id}`}>
                    <span className="payouts__when">
                      {s.paid_at ? `Paid ${formatDate(s.paid_at)}` : "Not paid yet"}
                      <span className="rows__sub">
                        Statement {formatDate(s.statement_time)}
                        {off ? <>{", difference "}<Figure amount={s.difference} review /></> : null}
                      </span>
                    </span>
                    <span className="payouts__figures">
                      <StatusChip status={s.reconcile_status} />
                      <Figure amount={s.payable_amount} />
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <Pager
        next={next ? `/shops/${shopId}/payouts?${new URLSearchParams({ cursor: next })}` : null}
        first={cursor ? `/shops/${shopId}/payouts` : null}
        nextLabel="Older payouts"
        label="Payout pages"
      />
    </section>
  );
}

/**
 * Payouts TikTok lists with no statement naming them (A36.2 answer 2). There is no statement
 * to explain them, so they open nothing.
 *
 * @param {{ payouts: NonNullable<import("@/lib/api-types").operations["listSettlements"]["responses"]["200"]["content"]["application/json"]["unmatched"]> }} props
 */
function Unmatched({ payouts }) {
  return (
    <>
      <h2 className="overview__heading">Unmatched</h2>
      <div className="card" data-testid="payouts-unmatched">
        <p className="card__why">Paid by TikTok, on no statement yet. Checked again each day.</p>
        <ul className="rows">
          {payouts.map((u) => (
            <li key={u.tiktok_payment_id} data-testid="unmatched-row">
              <span>
                {u.paid_at ? `Paid ${formatDate(u.paid_at)}` : u.created_at ? `Created ${formatDate(u.created_at)}` : "Date not given"}
                <span className="rows__sub" style={{ display: "block" }}>Reference {u.tiktok_payment_id}</span>
              </span>
              <span className="payouts__figures"><StatusChip status="unmatched" /> <Figure amount={u.amount} /></span>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

/**
 * What TikTok has paid and what it still owes, from Today's `shop_money`, which the service
 * computes. It was the Shop Money card on Overview. Since A37 phase 3 the three figures sit
 * side by side, and the sum that ties them sits under them.
 *
 * @param {{ sm: ShopMoney }} props
 */
function PaidAndOwed({ sm }) {
  const awaiting = sm.awaiting_breakdown ?? [];
  const postage = sm.return_postage && sm.return_postage.amount_minor !== 0 ? sm.return_postage : null;
  return (
    <div className="card hero" data-testid="paid-and-owed">
      <div className="stats">
        <div><p className="stat__label">Paid out</p><p className="stat__value"><Figure amount={sm.paid_out} /></p></div>
        <div><p className="stat__label">Awaiting settlement</p><p className="stat__value"><Figure amount={sm.awaiting} /></p></div>
        <div><p className="stat__label">Net proceeds</p><p className="stat__value"><Figure amount={sm.generated} /></p></div>
      </div>
      <p className="hero__meta">
        <span>All time</span>
        <span>Paid out + awaiting = net proceeds{postage ? " less return shipping" : ""}</span>
        {postage && <span>Return shipping <Figure amount={postage} /></span>}
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
 * normal timing, so the status is Awaiting settlement and never a fault. When TikTok does not
 * answer, one quiet line says so, since the figures above are unaffected.
 *
 * Since A37 phase 3 this is the one place the weeks are shown; Where the money went showed
 * them too until then.
 *
 * @param {{ result: import("@/lib/api").ApiResult, shopId: string }} props
 */
function AwaitingSettlement({ result, shopId }) {
  if (!result.ok || !result.data) {
    return (
      <p className="rows__sub overview__note" data-testid="awaiting-settlement">
        {result.status === 409
          ? <>Expected payouts need the shop connected. <Link href={`/shops/${shopId}/connection-problem`}>Reconnect your shop</Link></>
          : "Expected payout dates are not available from TikTok just now."}
      </p>
    );
  }
  /** @type {import("@/lib/api-types").components["schemas"]["ExpectedPayouts"]} */
  const p = result.data;
  if (p.weeks.length === 0) return null;
  return (
    <>
      <h2 className="overview__heading">Expected from TikTok</h2>
      <div className="card" data-testid="awaiting-settlement">
        <p className="card__why">Not on a statement yet. TikTok&apos;s estimates, so they can change.</p>
        <ul className="rows">
          {p.weeks.map((w) => (
            <li key={w.week_starting}>
              <span>
                Week of {formatDate(w.week_starting)}
                {w.orders > 0 && <span className="rows__sub" style={{ display: "block" }}>{w.orders} {w.orders === 1 ? "order" : "orders"}</span>}
              </span>
              <span className="payouts__figures"><StatusChip status="awaiting_settlement" /> <Figure amount={w.amount} /></span>
            </li>
          ))}
          <li className="rows__total"><span>Total expected</span><Figure amount={p.total} /></li>
        </ul>
      </div>
    </>
  );
}

/**
 * Pro's review list. Each statement links to its own page, where the difference is explained.
 * Nothing is shown when every statement adds up, because Payouts' chips already say so.
 *
 * @param {{ data: { items: { settlement: import("@/lib/api-types").components["schemas"]["Settlement"], orders_settled: number, unexplained: import("@/lib/api-types").components["schemas"]["Money"] }[], total_needing_review: number }, shopId: string }} props
 */
function NeedsReview({ data, shopId }) {
  return (
    <>
      <h2 className="overview__heading">Needs review</h2>
      <div className="card" data-testid="payout-review">
        <p className="card__why">
          {data.total_needing_review === 1
            ? "One statement differs from its orders."
            : `${data.total_needing_review} statements differ from their orders. Largest first.`}
        </p>
        <ul className="rows">
          {data.items.map((i) => (
            <li key={i.settlement.id}>
              <Link className="rowlink rowlink--quiet" href={`/shops/${shopId}/payouts/${i.settlement.id}`}>
                Statement {formatDate(i.settlement.statement_time)}
              </Link>
              <Figure amount={{ ...i.unexplained, amount_minor: Math.abs(i.unexplained.amount_minor) }} unsigned review />
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
