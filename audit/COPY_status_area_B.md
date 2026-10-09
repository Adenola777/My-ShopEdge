# Copy audit status, Area B, 9 October 2026

This file records what became of every Major and Minor finding in Area B of `audit/COPY_audit_8_october.md`, the core shop screens. The owner approved fixing them on 9 October 2026. The eleven Blocking rows are left to their own work and are not listed. Each row was checked against the code as it stood on 9 October, after copy batches 1 to 3 and the other changes since the audit, by opening the file and searching for the quoted text.

**What was run.** `npm run lint`, `npm run check` and `npm run build` in `web`, `ruff check .` at the root, and the contract and handler smoke tests in `service`. All of them pass. **What was not run.** No changed screen was opened in a browser, so the new states on Money, Tax, Payout detail, Check returns, Discrepancies and the three forms are checked by the type checker and the build only.

## Counts

| Status | Rows | Major | Minor |
|---|---|---|---|
| already fixed | 95 | 39 | 56 |
| fixed now | 6 | 5 | 1 |
| kept | 3 | 0 | 3 |
| owner decision | 2 | 1 | 1 |
| needs building | 4 | 3 | 1 |
| needs Area D | 3 | 3 | 0 |
| **Total** | **113** | **51** | **62** |

"Needs Area D" marks a change to text or a link that the Python service produces, which Area D owns. "Owner decision" marks the open naming decision between A8.4 and A29.7.

## Findings

| # | Screen | Current text | Severity | Status | What was done, or why |
|---|---|---|---|---|---|
| 12 | Today, Shop Money | "Net proceeds, all time" | Major | already fixed | Copy batch 3 renamed the line, and the card now says it covers every sale MyShopEdge holds for the shop. |
| 13 | Today, Shop Money | "This card covers every sale MyShopEdge holds for this shop. It shows what TikTok has paid you, and what it still owes you." | Minor | already fixed | Copy batch 3 made it two full sentences that state the card covers all time. |
| 14 | Today, Shop Money | "Return shipping TikTok deducted" | Major | already fixed | Copy batch 3 replaced "Return postage deducted" with the audit's wording. |
| 15 | Today, Shop Money | `sm.return_postage && sm.return_postage.amount_minor !== 0` | Minor | already fixed | The line now shows only when the amount is not zero, as A8.5 asks. |
| 16 | Today and Payouts | "Paid out" (Today, Payouts); "Payout" (Money, from money_lines.py) | Major | owner decision | "Paid out" against "Settled to your bank" is the open A8.4 against A29.7 decision, so nothing was renamed. |
| 17 | Today | "Shop Money" | Minor | owner decision | "Shop Money" against "Settlement" is part of the same open A8.4 against A29.7 decision. |
| 18 | Today, month | "Gross profit after returns this month", with the reason under it | Major | already fixed | The label now stays and the reason sits underneath it in its own line. |
| 19 | Today, hero | "This is net proceeds, because not every product sold today has a cost price yet." | Minor | already fixed | Copy batch 3 used the audit's sentence. |
| 20 | Today, freshness banner | "MyShopEdge last brought these figures up to date {time}, more than a day ago, so they may not be current." | Major | fixed now | The banner now shows only when freshness is `stale`, because `getting_old` covers most of every day under a daily read; the top bar still shows the time of the last read, and the audit's "each morning" sentence was not used because webhooks and the first read also bring a shop up to date. |
| 21 | Today, awaiting breakdown | `AWAITING[a.status] ?? "Awaiting settlement"` | Minor | already fixed | An unknown TikTok status now falls back to "Awaiting settlement". |
| 22 | Today, Needs your attention | `n.label ?? "Something needs your attention"` | Minor | already fixed | A missing label now falls back to words rather than the item's type. |
| 23 | Today, Needs your attention | "{amount} is affected." | Minor | already fixed | The fragment is now a sentence. |
| 24 | Today and Notifications | "Act now" / "Check" / "Note" on both screens | Minor | already fixed | Notifications now uses the same three words as Today. |
| 25 | Today, Needs you item | "Your TikTok Shop needs reconnecting" (today_view.py, no href) | Major | needs Area D | The label has no full stop and no next step, and `needs_href` in today_view.py gives `connection_action_required` no link; both are service output, so Area D owns the change (suggested: link to `/shops/{id}/connection-problem` and add "Reconnect it in Settings."). |
| 26 | Today, Needs you item | "TikTok would not renew MyShopEdge's access to your shop. Reconnect the shop to keep your figures up to date." | Major | already fixed | Batch 3 in today_view.py removed TikTok's error code and added the next step. |
| 27 | Today, Needs you item | "TikTok has not given MyShopEdge all the access it needs. Reconnect the shop and approve every permission on TikTok's page." | Major | already fixed | Batch 3 in today_view.py removed the scope identifiers. |
| 28 | Today, Needs you item | "Your figures may be out of date. MyShopEdge last brought them up to date {n} hours ago." | Minor | already fixed | Batch 3 in today_view.py gave both sentences a subject and a full stop. |
| 29 | Today, Needs you item | "{n} fee this month has a name MyShopEdge does not recognise" | Major | already fixed | Batch 3 in today_view.py replaced "has no category". |
| 30 | Today, Needs you item | "{n} return is waiting to be checked" (no href) | Major | needs Area D | The wording is fixed, but `needs_href` in today_view.py still gives `returns_to_check` no link, and the link is service output (suggested: `/shops/{id}/returns`). |
| 31 | Money, header | "This shows where every pound went from {from} to {to}." | Minor | already fixed | Copy batch 3 used the audit's sentence, with "on {date}" for the one-day view. |
| 32 | Money, basis switch | "Sales basis counts money on the day of the sale." (under the switch) | Minor | already fixed | The explanation now sits directly under the basis switch. |
| 33 | Money, footnote | "Cash basis counts money in the month TikTok settled it." | Minor | kept | The cash basis filters on `settlement_month`, which holds the first day of the month a payout settled (tiktok_sync.london_month), so "month" is true and the audit's "on the date" would be false. |
| 34 | Money, Held and paid out | "Reserve withheld", shown unsigned on Money, Payouts and Payout detail | Major | already fixed | Copy batch 2 gave the reserve one name and dropped the ledger sign through `Figure unsigned`. |
| 35 | Money, expected payouts | "This shop is not connected to TikTok, so MyShopEdge cannot ask TikTok what it expects to pay." with "Reconnect your shop" | Major | already fixed | The card now names the consequence and links to Connection problem. |
| 36 | Money, expected payouts | "These are TikTok's own estimates of {total} still to come..." | Minor | already fixed | The paragraph now shows only when TikTok lists at least one week. |
| 37 | Money and Today | "TikTok works these figures out itself, so they can differ from Awaiting settlement on Today..." | Major | already fixed | The card now says why the two figures can differ. |
| 38 | Money, empty | (no sections, reason only in the footnote) | Major | fixed now | Money now shows a state card, "There is nothing to break down for these dates.", with a line for each basis, when the service returns no sections. |
| 39 | Money, unmapped fee note | "See the fee" / "See the fees" | Minor | already fixed | The note now links to Records filtered by `unmapped_fee` for the period. |
| 40 | Payouts list | "Statement total" | Minor | already fixed | Both Payouts and Payout detail now say "Statement total". |
| 41 | Payouts list | `STATUS[...] ?? "Status not known"` | Minor | already fixed | An unknown payment status now reads "Status not known". |
| 42 | Payout detail | "Shipping cost charged by TikTok" | Major | already fixed | The bare "Shipping" now says whose charge it is. |
| 43 | Payout detail | "TikTok adjustments" | Minor | already fixed | The label now matches Money's "TikTok adjustment". |
| 44 | Payout detail | "Not explained by TikTok" | Major | already fixed | Payout detail now shows `components.difference` when it is not zero. |
| 45 | Payout detail | "Do the orders add up to this statement?" | Minor | already fixed | The heading no longer uses "reconcile". |
| 46 | Payout detail | "The orders behind this statement differ from it by {amount}. MyShopEdge shows the difference as Unexplained rather than hiding it." | Major | needs building | The sentence now names the amount, but no code raises a discrepancy for a statement that does not reconcile, so the link to Discrepancies that A18.3 asks for would lead nowhere; raising that discrepancy needs building first. |
| 47 | Invoice form | "Edit this invoice" | Minor | already fixed | The button no longer implies the invoice is wrong. |
| 48 | Invoice form | "The invoice was not saved. Check the figures and try again." | Minor | already fixed | The fallback now gives a next step. |
| 49 | Invoice form | "MyShopEdge checks that the gross equals the net plus the VAT, and keeps these figures. It does not keep a copy of the PDF." | Minor | already fixed | The six-year promise is gone, and the footnote says the PDF is not kept. |
| 50 | Invoice form | "Type, as the invoice names it" (no placeholder) | Minor | already fixed | The unconfirmed example "Platform Service Fee" was removed. |
| 51 | Products | "Ranked by gross profit after returns, {from} to {to}." | Major | already fixed | The heading now states the period the service used. |
| 52 | Products | visually hidden "{figure name}: " before each figure | Major | already fixed | Each row's figure now carries a hidden label for screen readers. |
| 53 | Products | "This product has no cost price for some of its sales in this period. Its net proceeds are {amount}." | Minor | already fixed | The fragment is now two sentences, which also fit costs that apply from a date. |
| 54 | Products | "Total gross profit after returns" / "Total across products" | Minor | already fixed | The total now says what it totals. |
| 55 | Products | "{n} more products came to {amount} between them. The total above includes them." | Minor | already fixed | The sentence has a verb, and products.py builds `others` as total less shown, so the inclusion is true. |
| 56 | Products and Product detail | "Untitled product" | Minor | already fixed | Products, Product detail and Stock fall back to "Untitled product" rather than a TikTok identifier. |
| 57 | Product detail | "Stock on hand is {n}." | Major | already fixed | The withdrawn "on the shelf" is gone. |
| 58 | Product detail | "{n} units sold from {from} to {to}" and the card heading "{from} to {to}" | Major | already fixed | Both now state the period. |
| 59 | Product detail | `<LineLabel line={l} />` on every product line | Major | already fixed | An unrecognised fee now reads "Fee MyShopEdge does not recognise" with TikTok's name beneath it. |
| 60 | Product detail | "Sales after refunds" (products.py SECTIONS) | Major | needs Area D | The product calculator in products.py still puts refunds before TikTok fees under a subtotal A8 does not have; reordering it to A8.5 changes service output and is Area D's. |
| 61 | Product detail | heading "One unit, pound by pound", no "per unit" suffix | Minor | already fixed | The card heading carries "one unit" and the suffix on the last subtotal is gone. |
| 62 | Product detail | "This variant has no seller SKU." | Minor | already fixed | The two facts were separated and the fragment is now a sentence. |
| 63 | Product detail | "See every record behind these figures" (passes from, to, basis) | Major | already fixed | The link now passes the product's period and basis, so the records match the figures. |
| 64 | Product transactions | "Records for this product" / "These are the records behind this product's figures from {from} to {to}." | Minor | already fixed | The screen now says "records" throughout and names its dates, or says it shows all records when none were passed. |
| 65 | Product transactions | `e.label ?? "Record"` and `RECORD_SOURCE[e.source]` | Major | already fixed | Sources now read "From TikTok", "Entered by you" or "Worked out by MyShopEdge", and an unlabelled entry reads "Record". |
| 66 | Records | `e.label ?? "Record"` | Major | already fixed | Records no longer falls back to a category or entry type code. |
| 67 | Records | "These are the records that make up the figure." | Minor | already fixed | "Ledger" is gone. |
| 68 | Records | "Money" (back link) | Minor | kept | The link names the screen it opens, which is the audit's second option, and Records sits under Money in the menu; a referrer-based "Back" would depend on the browser. |
| 69 | Records | "No records match these filters." (opened without a figure) | Minor | already fixed | Opened from the menu, Records now gives the filter sentence rather than one about a figure. |
| 70 | Glossary | `RULE_LABEL[r.rule_key]`, for example "Class 4 National Insurance" | Major | already fixed | Copy batch 1 named each rule in words. |
| 71 | Glossary | (18 terms) | Major | already fixed | Copy batch 3 added Seller discounts, Net sales, Total TikTok fees, Gross profit, Cost of goods sold, Paid out, Awaiting settlement, Reserve withheld and Return costs. |
| 72 | Glossary | "Sales basis counts money on the day of the sale." and the rest | Minor | already fixed | Every definition is now a sentence. |
| 73 | Glossary | "No tax rules are loaded yet." | Major | already fixed | The unbacked "will appear here shortly" is gone. |
| 74 | Glossary | "{rule name} on gov.uk (opens in a new tab)" | Minor | already fixed | The link text now names the rule and says it opens a new tab. |
| 75 | Glossary | "Glossary and tax rules" (page title and heading) | Minor | already fixed | The page is renamed; the menu entry "Help and glossary" is in lib/nav.js, which the shell's audit area covers. |
| 76 | Stock | "This is your stock as TikTok last reported it, with your own adjustments. The newest count is from {date}." | Minor | already fixed | Both sentences have verbs, and the count time shows only when there are items. |
| 77 | Stock | "Check returns" (Stock link, Returns title and heading) | Minor | already fixed | Both shop screens now say "Check returns"; the menu entry "Returns" is in lib/nav.js, which the shell's audit area covers. |
| 78 | Stock | "Low means fewer days of cover than your low stock alert, which is fourteen days unless you change it." | Minor | already fixed | The explainer now names the threshold and links to Alerts; stock.py confirms the default of 14. |
| 79 | Stock | "{n} day" / "{n} days of cover" | Minor | already fixed | The word now follows the number. |
| 80 | Stock movements | "TikTok's count rose, so MyShopEdge reduced your adjustment" | Major | already fixed | "Absorbed" is gone from the movement name. |
| 81 | Adjust form | "...If you add units here and TikTok's count later rises by no more than your alert setting allows, MyShopEdge takes those units off your adjustment..." | Major | already fixed | The form now says a later TikTok count can take the adjustment back, and that a larger rise goes to Discrepancies. |
| 82 | Adjust form | "Units to add, or a minus number to remove" | Minor | already fixed | The label now says how to remove units. |
| 83 | Stock movements | "Belongs to an order" / "Belongs to a return" | Minor | needs building | A stock movement carries MyShopEdge's own order id and not TikTok's order number, so showing which order needs the service to serve that number. |
| 84 | Return check | "Each item can be checked only once, and the check cannot be changed." | Major | already fixed | The cryptic "Stock updates once." is gone. |
| 85 | Return check | "Refund to the customer" | Minor | already fixed | The row now follows A8. |
| 86 | Return check form | `useState(null)` with "Say how the item came back before you record the check." | Major | already fixed | Nothing is preselected, and the form refuses to record without a choice. |
| 87 | Return check form | "Record this check" | Major | already fixed | The button now says what it does. |
| 88 | Return check form | "How did it come back?" (visible) | Minor | already fixed | The question is now visible and labels the choices. |
| 89 | Return check form | "What this check records" / "{units} at the cost in force when they sold" | Minor | already fixed | The heading is no longer a fragment and the pronoun follows the count. |
| 90 | Return check form | `formatMoney({ amount_minor: shownPostage, currency })` | Minor | already fixed | The card now formats the parsed pence, so "2" shows as £2.00. |
| 91 | Return check form | "Return shipping you paid (£)" | Minor | already fixed | The label now follows A8.4. |
| 92 | Notifications | "MyShopEdge tells you here when an item runs low on stock, when a return has waited..." | Major | already fixed | The empty state lists only notices the service writes; each type was confirmed in alert_notices.py, export_schedules.py, order_usage.py, tiktok_sync.py and tiktok_webhooks.py. |
| 93 | Notifications | "You have no open notices." | Major | already fixed | The empty state no longer contradicts Today's list. |
| 94 | Notifications | `noticeLink(n, shopId)` | Major | already fixed | Each notice whose writer sets an entity now links to its screen. |
| 95 | Notifications | "You have no unread notices." / "You have {n} unread notices." | Minor | already fixed | Both are now sentences. |
| 96 | Notifications | "Mark as resolved" | Minor | already fixed | The action now matches the Resolved tab. |
| 97 | Notifications | "TikTok's count for {title} rose by {n} units. You had already added {n} units in MyShopEdge, so MyShopEdge removed them..." | Major | already fixed | Batch 3 in tiktok_sync.py rewrote the notice without "On the shelf" and without guessing what the seller did. |
| 98 | Discrepancies | "While one is open, MyShopEdge uses the value shown under \"MyShopEdge is using\"." | Major | already fixed | The sentence no longer claims totals always use TikTok's value. |
| 99 | Discrepancies, unmapped fee | "TikTok charged a fee MyShopEdge does not recognise. Your figures include it in full, under TikTok's own name." | Major | already fixed | "We are identifying it" is gone. That no code raises an `unmapped_fee` discrepancy (CLR-4) is still true and is a build item, not copy. |
| 100 | Discrepancies, unmapped fee | "TikTok calls it" {tiktok_value} | Major | needs building | The label is fixed, but A18.4 also wants the amount and the statement date, and the Discrepancy schema carries neither, so the service must serve them first. |
| 101 | Discrepancies, unmapped fee | only "Mark as explained" for an unrecognised fee | Major | already fixed | `explainOnly` hides the two choices that do not apply. |
| 102 | Discrepancies | "TikTok" {value}, "Your record" {value}, with units for a stock count | Major | needs building | A stock count now reads "12 units", but an amount such as "-5.00" stays bare because the Discrepancy schema carries no currency, and adding a pound sign here would be an assumption. |
| 103 | Discrepancies | "TikTok recorded this under the type \"platform penalty\" and gave no further reason." | Minor | already fixed | Batch 3 in tiktok_sync.py turned the code into words. |
| 104 | Discrepancies | "a record" | Minor | already fixed | "A ledger line" is gone. |
| 105 | Discrepancies | "No open discrepancies." with "MyShopEdge has found nothing in your records that disagrees with TikTok." | Minor | already fixed | The empty state now has a body. |
| 106 | Resolve actions | "The correct value, as it should read on your record" | Major | already fixed | The field label now says what to type. |
| 107 | Tax | "This page tracks your sales against the VAT threshold, estimates tax to set aside and lists your tax dates. It is not financial advice." | Minor | already fixed | The fragments are now sentences and the set-aside is mentioned. |
| 108 | Tax | "The VAT threshold is not loaded yet, so your position cannot be shown." | Major | already fixed | The unbacked "shortly" is gone. |
| 109 | Tax | "Tax dates are not loaded yet." / "Tax dates could not be loaded just now." | Major | already fixed | The unbacked "shortly" is gone, and a failed read no longer reads as "not loaded". |
| 110 | Tax | (set-aside card hidden on error) | Major | fixed now | A failed set-aside read now shows the card with "MyShopEdge could not load the set-aside estimate just now. Nothing on your account has changed, and the other figures on this page are unaffected. Try again in a moment." |
| 111 | Tax | "Fill in your business details so MyShopEdge can estimate a set-aside." | Major | fixed now | The service text was already fixed; the card now adds the link "Fill in your business details" to `setup/tax` when `unavailable_reason` is `no_tax_profile`. |
| 112 | Tax | "Some products you sold have no cost price, so your gross profit after returns is not known." | Minor | fixed now | The card now adds the link "Add costs" to Products when `unavailable_reason` is `incomplete_costs`. |
| 113 | Tax | "Gross profit after returns so far this tax year, by sale date, before your overheads" | Minor | already fixed | Batch 3 in tax.py put the A8 term in the label. |
| 114 | Tax | "Gross sales over the last twelve months" | Minor | already fixed | The term is now explained in words, and tax.py confirms it sums gross sales. |
| 115 | Figure | "Not known" | Minor | already fixed | The em dash glyph is gone. |
| 116 | Figure | `reason \|\| "Not known"` | Minor | already fixed | The default no longer implies the figure will become known. |
| 117 | terms | "Not current" | Minor | already fixed | "Getting old" is gone from lib/terms.js. |
| 118 | terms | `CONFIDENCE_MEANING` titles on the chips | Minor | already fixed | The Estimated and Incomplete chips now carry a title saying what each means. |
| 119 | Cost form | "Cost price per unit for {variant name}" | Major | already fixed | Each variant's input now has its own accessible name. |
| 120 | Cost form | placeholder "0.00" | Minor | already fixed | The placeholder no longer looks like a stored cost. |
| 121 | All forms | (no success message) | Major | fixed now | The cost, adjustment and invoice forms now say what was saved, and Check returns and Discrepancies show a notice of what was recorded, passed through the address because the checked item leaves the list. |
| 122 | All screens | loading.jsx and error.jsx under `shops/[shopId]` | Major | already fixed | Loading, error and not-found pages were added on 8 October (commit 042a701). |
| 123 | LineLabel / Money / Records / terms | "Fee MyShopEdge does not recognise" (LineLabel, money_lines.py, terms.js) | Minor | already fixed | One name is now used on every screen. |
| 124 | Layout | (no strings in layout.jsx) | Minor | kept | The audit's own suggestion is no change; the menu labels it mentions are in lib/nav.js, which the shell's audit area covers. |

## Missing states, per screen

The audit's table of loading, empty, error and success states, as each stands now. Since 8 October `web/src/app/shops/[shopId]/loading.jsx` and `error.jsx` give every shop screen a loading state and an error page (commit 042a701), so the Loading column is met on every row and is not repeated below.

| Screen | Empty | Error | Success | Status |
|---|---|---|---|---|
| Today | Needs you says "Nothing needs your attention right now."; a shop never read gets "Your shop has not been brought up to date yet, so these figures are not complete." | `ApiProblem` | n/a | already fixed |
| Money | A period with no sections now shows "There is nothing to break down for these dates." | `ApiProblem`; Expected payouts has its own card | n/a | fixed now |
| Payouts | Present | `ApiProblem` | n/a | already fixed |
| Payout detail | "No invoice is recorded for this payout yet." | `ApiProblem` | The invoice form now says "The invoice is saved." | fixed now |
| Products | Present, and the heading names the period | `ApiProblem` | n/a | already fixed |
| Product detail | The period card now says "MyShopEdge holds no sales of this product for these dates." when it has no sections | `ApiProblem` | The cost form now says "The cost of {amount} is saved for units sold from {date}." | fixed now |
| Product transactions | Says the dates, or says it shows every record | `ApiProblem` | n/a | already fixed |
| Records | Opened without a figure, says "No records match these filters." | `ApiProblem` | n/a | already fixed |
| Stock | Present for no stock and for a filter | `ApiProblem` | n/a | already fixed |
| Stock movements | Present | `ApiProblem` | The adjust form now says "The adjustment is saved." and how the count moved | fixed now |
| Returns | Present | `ApiProblem` | The page now says what the check recorded for each of the three choices | fixed now |
| Notifications | "You have no open notices." with the notices the service writes | `ApiProblem`; per row error | Marking a notice read changes its row, and marking it resolved moves it to the Resolved tab | already fixed |
| Discrepancies | "No open discrepancies." with a body | `ApiProblem` | The page now says what the resolution recorded and that no total changed | fixed now |
| Tax | VAT and dates say plainly when rules are not loaded | The set-aside card now stays with an error line; a failed dates read says "could not be loaded just now" | n/a | fixed now |
| Glossary | "No tax rules are loaded yet." | `ApiProblem` | n/a | already fixed |

## Glossary consistency

| Term | Where it stands now | Status |
|---|---|---|
| Paid out (A29.7) / Settled to your bank (A8.4) | "Paid out" on Today, Payouts and Payout detail, and "Payout" on Money from `money_lines.LABELS["settlement"]` | owner decision |
| Reserve withheld | "Reserve withheld", unsigned, on Money, Payouts and Payout detail | already fixed |
| Return shipping you paid | "Return shipping you paid" on the return check and in `money_lines.py`; Today says "Return shipping TikTok deducted" for the part TikTok settled, which A29.7 states separately | already fixed |
| Total TikTok fees | Payout detail lists each fee with "Total TikTok fees" under them; a statement whose ledger holds no fee lines keeps one "Fees" line so no amount drops off | already fixed |
| Refunds to customers | "Refunds to customers" as a line and "Refund to the customer" on one return; Money's section heading is "Refunds" in `money_view.CHAIN` | already fixed |
| Gross profit after returns | Products switch, Today, Tax and Money all use it | already fixed |
| Stock on hand | Product detail says "Stock on hand is {n}", Stock says "{n} on hand", and the stock notice says "Stock on hand is {n}" | already fixed |
| Net proceeds | Today's all-time figure is "Net proceeds, all time" | already fixed |
| Unrecognised fee | "Fee MyShopEdge does not recognise" everywhere, and "has a name MyShopEdge does not recognise" in sentences | already fixed |
| Shop Money (A29.7) / Settlement (A8.4) | "Shop Money" on Today, "Settlement" defined in the glossary | owner decision |
| Severity | "Act now", "Check" and "Note" on Today and Notifications | already fixed |
| Return check | "Check returns" on Stock and on the screen itself; the menu entry "Returns" is in `lib/nav.js`, which the shell's audit area covers | already fixed |
| Tax profile | `tax.py` now says "business details", which matches the menu | already fixed |
| Payouts page | The menu says "Payouts and invoices", Money's button says "Payouts and fee invoices" and the page says "Payouts"; this waits on the Paid out naming above, and the menu is the shell's | owner decision |
| Resolved | "Mark as resolved" and the Resolved tab | already fixed |
