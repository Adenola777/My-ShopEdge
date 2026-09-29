# Action 31. Rulings of 29 September 2026

## 31.1 The insights getInsights serves

**The question.** The SRD requires "the four MVP insights" under FI-4 and cites Section 24,
which is not in this repository. No document names all four. Two are evidenced:

- The QA document's DSH-6 case: "Clay Mask: postage and packing £2.51 on £9.25; stock £3.20.
  Insight states postage share 27p in the £1; no claim that posting costs more than making."
- The wireframes: "Negative Contribution shown in full, with an insight offering options."

Neither document gives the point at which an insight should appear.

**Ruling.** Build the two evidenced rules. The other two stay unbuilt, and are recorded here
as unnamed, until the owner names them.

- **`negative_contribution`**, severity warning. A product whose Contribution, as A4 defines
  it, is below zero in the period. Contribution is worked out only when every variant sold
  has a cost. The text offers options rather than an instruction.
- **`postage_share`**, severity info. For every costed product, postage and packing as pence
  in the £1 of what reached the shop. There is no threshold. Postage and packing are the
  seller's own per-unit figures in `product_costs`, and "reached the shop" is sales after the
  seller's discounts, before TikTok's cut, as the G5 case shows.

**Built.** `service/app/insights.py`, with `tests/test_insights_trends.py` holding the Clay
Mask case, which reads 27p. The period is the current London month to date, because the
contract gives the operation no period parameter.

## 31.2 Readings taken while building getTrends

These are readings of the contract rather than rulings by the owner, recorded so that they
can be corrected.

- **`units` is a count.** The contract typed every trend point as Money, which cannot carry a
  unit count. The contract was amended: `count` carries units, and `value` may be null when a
  month's figure is not known.
- **"Before the shop connected".** The contract marks such a month incomplete. The history
  TikTok hands over at connection reaches back before the shop row was made, so the first
  month the ledger holds is taken as where the shop's data begins.

## 31.3 Two operations added to the contract while building

- **`getAccountExport`**, `GET /me/export/{exportId}`. requestAccountExport says "Poll the
  job", and the contract gave no operation to poll it with.
- **`listSkuCosts`**, `GET /shops/{shopId}/costs`. A3's S20 lists every variant with its units
  sold in the last 30 days and its cost. `top_missing` stops at ten and the stock list
  carries no cost, so nothing gave that list.

## 31.4 The cost a unit carries, CLAUDE.md fault 10

**The question.** On 28 September the owner approved costing a period at the cost in force
at its end. The year dataset then showed that a year read that way prices units sold the
previous October at a cost that took effect in July, so twelve monthly kept figures cannot
sum to the year and the tax-year set-aside carries today's cost.

**Ruling, 29 September 2026.** Each unit is costed at the cost in force on its sale date, the
London date of its order. A returned unit takes off the cost of its original sale, dated by
that order. This replaces the period-end rule for every figure.

**Built.**

- `products.py` costs each sold line and each returned item on its own sale date, by
  `effective_from` with `created_at` as the tie-break, which is what `checkReturnItem`
  already did for a write-off. Retained cost per variant is the cost sold less the cost
  returned, floored at zero. A variant with any unit sold or returned without a cost on its
  sale date leaves kept unknown. Money, Today, trends, exports and the set-aside read kept
  through this query, so all of them follow.
- `costs.py` coverage counts a unit as costed when a cost was in force on its sale date. A
  variant is listed as missing a cost when any unit it sold in the period had none.
- `insights.py` takes postage and packing from the row in force on each unit's sale date.
- The cost shown beside a variant on S20 and on the product detail is still today's cost,
  because those screens show what the seller would edit rather than a figure.

**Checked, 29 September 2026.** `testdata/year_check.py` passes all 24 checks on a database
built from empty, including a new one that the monthly kept figures sum to the kept of the
months read as one span. On the local copy of development, with every cost in force before
every sale, the old and new product queries returned identical rows on both bases. With a
cost of 99,999 taking effect on 10 August for one variant, inside a transaction that was
rolled back, the new query gave that variant's retained cost as 10,200. An independent
calculation gives the same: two units at 5,100 and one at 99,999, less one returned unit
at 99,999. The old query gave 199,998. In the same rolled-back transaction, coverage read
one of that variant's three units as costed, and insights put postage and packing on the
one unit sold after 10 August and marked the product's postage unknown.

## 31.5 When a live order reaches the ledger

**The question.** The ledger is append-only (LED-1), so no row can be given its statement
after it is written. TikTok states an order's final fees only when the order settles, and its
own unsettled endpoint warns that every amount it returns may change before settlement (A22).
A sale posted when the order arrived could therefore never be linked to its settlement or
corrected, except by reversing it and posting it again.

**Ruling, 29 September 2026.** Order money enters the ledger once, at settlement, already
carrying its statement and the London month it settled. Nothing is ever reversed. Unsettled
orders are held outside the ledger. The owner accepted the consequence: a sale shows on the
sales basis only once it settles, so recent weeks read low and are marked incomplete.

**Built.** `service/app/tiktok_sync.py`. Orders, products, variants and lines, and returns
with their items, are written as they arrive and post nothing. Each statement is read once:
the per-order calculator gives every order's SKU breakdown, and each entry is posted with
the statement. A statement already posted is never posted again. Holding unsettled orders
with TikTok's estimate, which getExpectedPayouts needs, is not built yet.

**Checked, 29 September 2026.** `testdata/tiktok_sync_check.py` ran the whole sync, through a
transport answering from the generated payloads, into a database built from empty. On both
the two-month and the year datasets, all 36 checks passed. The ledger it wrote equalled the
settled part of the independent ingester's `rows.json` category by category, every entry
carried its settlement, a second run wrote nothing, and the refresh stored new tokens
encrypted and recorded a refused refresh with TikTok's code. None of it has reached TikTok,
and several request details are unverified and named as such in `tiktok_api.py`.

## 31.6 The core shop is GBGBLCRKQTEX

**Ruling, 29 September 2026.** The owner's live UK shop, `GBGBLCRKQTEX` ("My ShopEdge" in
Seller Center), is the core shop for this repository. The Indonesian sandbox shop
`7495568017912465932`, which the ISV app returned on 23 September (A19.2, A24.2), is not
used for anything and is kept in A11 and A19 only as history.

**What already held.** Nothing in the code or the databases was tied to the Indonesian shop.
`connections.py` accepts a shop only when TikTok reports region `GB` and seller type `LOCAL`,
production held no shops when queried on 29 September, and the development branch holds only
the synthetic and demo shops. The binding that returned the Indonesian shop lives in Partner
Center, where that shop is authorised to the ISV app.

**How the core shop connects.** Through a Seller Developer custom app created on the seller
account that owns `GBGBLCRKQTEX` (A24.3). It binds to that shop alone and needs no marketplace
review. Its service ID, app key and app secret take the place of the ISV app's values on the
Render service, and `RUNBOOK_tiktok_connection.md` step 1 is followed with that app. The code
is the same for both apps (A24.3).

**Unverified.** Whether a Seller Developer custom app authorises through the same
`services.tiktokshop.com` link, and returns `user_type` 0, is not recorded anywhere in this
repository. The first connection answers it: `connections.py` refuses any other `user_type`
with `not_a_seller_account`.

**Answered, 29 September 2026.** The custom app authorised through the same link. At 17:52 UTC
the callback accepted the shop `7494930319769175829`, named IkonetU, with region `GB` and seller
type `LOCAL`. TikTok must have returned `user_type` 0, because `connections.py` refuses any other value
before it stores anything, and the shop and its encrypted tokens were on production when
queried afterwards. The same authorisation showed that TikTok's `*_expire_in` fields are Unix
times rather than durations, which is CLAUDE.md fault 11.

**Corrected, 29 September 2026.** The shop that connected is not the one this ruling names.
Production holds shop code `GBGBLCUKQTCE`, IkonetU, TikTok shop id `7494930319769175829`. The
owner's Seller Center shows `GBGBLCRKQTEX`. Both are the owner's, and he wants both (31.7).

## 31.7 An account holds every shop its authorisation covers

**Ruling, 29 September 2026.** The owner wants both IkonetU (`GBGBLCUKQTCE`) and
`GBGBLCRKQTEX` connected to his account. This replaces A12.7's one shop per account.

**Built.** The callback stores every shop TikTok's Get Authorized Shops returns, each with its
own row, its own cipher and the same tokens, written in one transaction so they share
`authorised_at`. A refresh writes the new tokens to every unrevoked connection with that
`authorised_at`, because whether TikTok voids the old refresh token is unverified. The callback
logs each shop's code, name, region and seller type, and never a token. The contract still
returns one shop, the first accepted one. Nothing in the schema limited an account to one shop.

**Unverified.** Whether one authorisation of the custom app lists both shops. The first
authorisation returned IkonetU, and how many shops its list held was not logged. If the next
connection stores only IkonetU, `GBGBLCRKQTEX` needs a custom app of its own, and the service,
which holds one app key, would need to hold two.

**Also found by the first sync, 29 September 2026.** TikTok's returns search refuses a
`page_size` of 100, code 98001004, allowed range 10 to 50. Orders and statements accepted 100.
The returns search now asks for 50. The same run read 0 orders and 0 statements for IkonetU
over two years, and whether that is the shop's real history is not known.
