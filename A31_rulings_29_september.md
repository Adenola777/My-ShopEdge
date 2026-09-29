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
