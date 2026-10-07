# A33. What TikTok's Get Unsettled Transactions returns, and how expected payouts are read

Written 7 October 2026. `getExpectedPayouts` was the one contract operation not served,
because nothing read TikTok's unsettled orders. The owner pasted TikTok's page for the
endpoint the same day, and this records the facts the read is built on.

## 33.1 The facts, and where each came from

| Fact | Source |
|---|---|
| Path `/finance/202507/orders/unsettled`, scope `seller.finance.info` | TikTok's Get Unsettled Transactions page, pasted by the owner on 7 October |
| The method is GET, and every parameter goes in the query string | The request example on the same page |
| `sort_field` is required and accepts only `order_create_time`. `sort_order` defaults to ASC | The same page's parameter table. Its request example sends a timestamp as `sort_field`, which contradicts the table, so the table is followed |
| `page_size` 1 to 100, default 20. `page_token` takes the previous `next_page_token` | The same page |
| `search_time_ge` and `search_time_lt` filter by creation time, and the first defaults to 1 January 2025 | The same page |
| Only transactions created after 1 January 2025 are returned. A settled transaction leaves the list | The same page |
| Every amount is an estimate that may change before settlement | The same page |
| `data` holds `next_page_token`, `total_count`, four `sum_est_*` totals and `transactions[]`. Each transaction holds `type` (ORDER in the example), `id`, `status`, `currency`, `estimated_settlement`, `order_id`, `adjustment_id`, `est_settlement_amount`, `est_revenue_amount`, `est_shipping_cost_amount`, `est_fee_tax_amount` and a breakdown of each | The response example on the same page |
| Both connected shops hold `seller.finance.info` | The statement sync, which needs it, has read both shops daily since 29 September |

## 33.2 What is not known

- **No real shop has been asked yet.** Every fact above comes from TikTok's page. A vendor's
  page is not a fact about this installation (CLAUDE.md rule 7), so the first answer from a
  real shop is the test.
- The example is in USD with whole-number amounts. The read takes every amount as a decimal
  string in pounds, the way GB statement amounts arrive ("458.38"), and refuses any currency
  but the shop's own.
- `estimated_settlement` is a string of Unix seconds in the example. A transaction without
  a usable value is left out of the weeks and the total, and the service logs how many.
- The example shows only `type` ORDER. An adjustment is assumed to carry type ADJUSTMENT,
  which the code uses only to leave adjustments out of the order count.

## 33.3 How the service uses it

`service/app/payouts.py` serves `getExpectedPayouts`. When the seller opens Money, it asks
TikTok for every unsettled transaction, a hundred at a time, oldest order first. It sums
`est_settlement_amount` by the London week (Monday) of `estimated_settlement`, counts
distinct orders per week, and labels the result `estimated`. No table holds a copy, so no
migration was needed. A shop with more than 5,000 unsettled transactions is refused rather
than shown a partial total. If TikTok does not answer, the Money screen says so in that one
card, and the rest of the page is unaffected.
