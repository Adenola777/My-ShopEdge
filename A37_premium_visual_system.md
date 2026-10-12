# A37. The premium visual system

Written 11 October 2026. That morning the owner asked for a UI audit of the authenticated app.
The audit compared the app with section 21 of his brief, "Visual and interaction rules", and
found that orange marked unchosen options, the page was pure white, the greys were slate, boxes
sat 12 px apart, and eight close type sizes left nothing leading the eye. He approved a warm
page and wider gaps the same morning, and then gave a full specification for a calm, premium
financial product. This file records his rulings on it. Where a ruling below conflicts with an
earlier one, this file wins for the point it names (A29.11).

## A37.1 The owner's rulings

| # | Subject | Ruling | Replaces |
|---|---|---|---|
| 1 | Font | Inter for text and figures, self-hosted from `@fontsource-variable/inter` 5.3.0, with tabular numerals for every amount, percentage, quantity and date | WFW 1.1 (Plus Jakarta Sans for text, Archivo for figures) |
| 2 | Gradients | No gradient outside the logo. The band along the top of every screen and the gradient bar on the active phone tab are removed; the active tab keeps a solid orange bar | A7.11 (the brand gradient as accents) |
| 3 | Orange | Orange marks the primary action, the selected state and key financial emphasis only. A choice in use is orange; the others are neutral | The switch styling of 24 September, which drew unchosen options in orange |
| 4 | Status colours | Pale green for complete or reconciled only. Pale amber for pending or review. Muted red for a write-off, a confirmed loss or a failure. Every status chip carries an icon as well as a colour | A7.10, which kept red, amber and green for the three payment statuses alone |
| 5 | Surfaces | The page, the navigation and every card are pure white (`#ffffff`), the main card included, and cards carry a 1 px neutral grey border (`#e5e7eb`). Orange is the highlight: the area and page in use in the navigation, and the choice in use on a switch, take the pale orange tint with orange text. Corners of 12 px on cards and 16 px on the main card. No shadow on a card. **Amended twice the same day:** the owner first approved a warm page (`#fffaf7`, rail `#fff5f0`, border `#f0e4dc`), then asked for white with no pink in it, then for the navigation and the boxes on white with orange as the highlight. He asked for the white Apple uses; Apple's colour guidelines, read that day, name the primary background colour for the overall view but give no numeric value, and apple.com could not be reached from the session, so `#ffffff` is used and Apple's exact value is **not verified** | The neutrals measured on 24 September (`#ffffff`, `#cbd5e1`, `#f1f5f9`) |
| 6 | Spacing | On a larger screen, 40 px page padding, 32 px at the top, 48 px between sections, 24 px between cards and inside a card, 32 px inside the main card. On a phone, 16 px padding and inside a card, 32 px between sections | The 16 px card padding and 12 px gaps of 24 September |
| 7 | Motion | Transitions of 150 to 220 ms, ease-out, and none when the browser asks for reduced motion. No counting figures, no pulsing, no bounce | Nothing; the reduced-motion rule of WFW 7 stands |
| 8 | Navigation | On a larger screen, each area with more than one page (Overview, Reconcile, Products, VAT and tax, Settings) is folded. Its pages appear only when the seller clicks the area's name, which turns a chevron, and a second click folds them again. The area in use stays marked in orange while folded. Areas sit 8 px apart and are 44 px high, and the pages under an area are 40 px high and 8 px apart. An area the seller opened stays open while they move between its pages. On a phone the bottom tabs and the row of pages above each page are unchanged | A36.1 item 4's rail, where the area in use opened on its own |
| 9 | Wording | Explanations in the app are short phrases, enough to understand once, not paragraphs. A form's help sits inside the empty field as a faint hint (`#64748b`, 4.76 : 1 on white) or in one short line under it. The glossary keeps full definitions, and the legal facts on the data and deletion pages keep their substance in fewer words. The house style of sentences with a subject and a verb still governs documents and messages; on the app's own screens the owner's ruling of 11 October 2026 lets a label or hint be a phrase | The longer explanations written since 24 September, of up to 57 words |

The waterfall's order and whether return costs stay in it were asked on 11 October 2026 and are
**not yet answered**. They belong to phase 2 and change nothing here.

## A37.2 The status chips

| Tone | Colour | Icon | Used for |
|---|---|---|---|
| good | pale green | ✓ | Reconciled, Complete, Matched, Connected, a finished read |
| warn | pale amber | ◷ | Awaiting settlement, Pending payment, Estimated, Being read |
| review | pale amber | ! | Needs review, Unmatched, Low, Out of stock, No match found, Duplicate, Invalid cost, Reconnect needed |
| cost | pale amber | + | Cost needed, Partially costed, Incomplete |
| delayed | pale amber | ↻ | Sync delayed, Not current, Out of date |
| bad | muted red | ! | Unsellable and written off, Payment did not go through, Could not be read, a critical notice |
| quiet | neutral | none | Healthy, Confirmed, Disconnected, Nothing came back, an informational notice |

The icon is drawn by CSS with empty alternative text, so a screen reader reads the word alone.
`Needs review` on a payout moved from red to amber, because a difference nobody has explained is
not yet a confirmed loss. The cost upload's `needs_review` row reads "Needs your confirmation",
the brief's wording.

## A37.3 Checked

Checked on 11 October 2026 by running the production build of the web app against the local
copy of the sample shop, at 1280 and 390 px, in Chromium:

- every text element on seven screens is Inter with tabular numerals, at six sizes (40, 28, 20,
  16, 15 and 14 px), and nothing is smaller than 14 px;
- no text on fourteen screens falls below WCAG AA contrast, where the main card's grey lines had
  measured 4.34 : 1;
- every gap between cards on eighteen screens is 24 px, a heading sits 8 to 12 px above the card
  it names, and no page scrolls sideways.

## A37.5 Phase 2, the Overview, started 11 October 2026

The owner ruled the same day that **return costs stay** in the waterfall, after gross profit,
so Gross profit after returns remains the Overview's main figure when costs are complete.

Built and checked so far, against the local copy at 1280 and 390 px:

- The title carries Export beside it, and the period and basis switches sit on one row on a
  larger screen. The update time is in the top bar and on the main card, and not repeated.
- The main card shows its amount, what it means, its cost coverage, its period, its basis and
  its last update, and one action as a button: View product performance, Review missing costs
  or Add product costs.
- Every waterfall line opens its records in a side panel (a native dialog: focus stays in it,
  Escape closes it, focus returns to the line). The panel shows the first twenty records and
  the total, which equalled the line on the line tested (Platform commission, -£427.80, 1 to 23
  August 2026, sales basis), and links to the full Transactions page. The line stays a link,
  so a new tab or a browser without JavaScript reaches the same records.

**The owner's rulings later the same day:**

- **Each TikTok fee stays on its own line.** The brief's four groups are not used, so the
  breakdown is never merged. Transaction fee and the shipping and packaging the seller pays keep
  their own lines too.
- **Figure colours, approved.** Every amount is dark, additions and deductions alike, and a
  deduction carries its minus sign. No figure is ever green. Red is kept for stock written off
  and a failed payment. A payout difference nobody has explained is amber (`money--review`,
  `#8A5A00`, 6.1 : 1 on white), matching its Needs review label.
- **The Overview is the premium first screen, with its explanations moved off it.** It holds
  the title and shop, Export, one row of compact period and basis switches, the main figure with
  its margin, period and basis and one action, the calculation as one statement in a single card
  (a small label per section, each closed by its subtotal, and no card per section), and what
  needs attention. What TikTok paid out is left to Reconcile. The definitions are in the
  glossary. Measured at 1280 px: 99 words, against about 140 before, and three cards, against
  eight. Section headings sit 48 px below what precedes them on a larger screen and 32 px on a
  phone, and stock written off is still red.

## A37.6 Phase 3, Reconcile, built 11 October 2026

On the owner's approval of the remaining phases the same day, Reconcile took the Overview's
pattern. Measured against the local copy at 1280 px, before and after:

| Screen | Words | Cards | Page height |
|---|---|---|---|
| Payouts | 240 to 115 | 18 to 2 | 5,423 to 1,832 px |
| Explain this payout | 237 to 105 | 6 to 4 | 2,958 to 1,794 px |
| Where the money went | 105 to 82 | 2 to 1 | 1,678 to 1,383 px |

- **Payouts.** Paid out, Awaiting settlement and Net proceeds sit side by side in one card,
  stacked on a phone. Needs review, Unmatched and Expected from TikTok appear only when they
  hold something. Every payout is one row of a single list: its date, its statement date, its
  status chip and its amount, with a difference shown in amber only when there is one. The
  whole row is the link.
- **Explain this payout.** The payout is the main figure, with its status, one short line on
  what the status means, and when the statement was issued, paid and read. The statement is
  one card of groups, each closed by its subtotal, and every TikTok fee keeps its own line. The
  check against the orders states the difference once, in amber, where the page had shown it
  twice and once in red. The orders and the invoice form are folded until clicked. An unpaid
  statement's last line reads To be paid rather than Paid out.
- **Where the money went.** The switches are the Overview's compact row and Export sits
  beside the title. Expected payouts by week are now shown on Payouts alone, which already
  showed the same weeks from the same call.
- **Transactions and Issues.** A record's date, order and TikTok's field name sit on one quiet
  line joined by a middle dot. Issues uses the compact switch and shorter wording.

Checked with lint, the type check, the production build and screenshots at 1280 and 390 px. No
page scrolls sideways. The local copy cannot reach TikTok, so Expected from TikTok was seen
only in its unavailable state, and Needs review and Unmatched were not seen with data.

## A37.7 Phase 4, Products, built 11 October 2026

- **The table.** It showed nine columns and was clipped at 1280 px, cutting off Gross profit
  after returns. It now has six: the product, with units sold and returned and any cost status
  under its name; net sales; TikTok deductions; product cost; return impact; and gross profit
  after returns with the margin under it. Measured at 1024, 1280 and 1440 px, the table fits
  its card with no sideways scroll. Below 960 px, where it did not fit, each product is one row
  with its gross profit and margin, and its page holds the rest.
- **The costs card** is one line with small buttons: Upload costs, Type in and Template.
- **The switch** reads Gross profit, Units and Returns; the line above it names the ranking in
  full, so the switch fits a phone's row.
- **A product's page.** Gross profit after returns comes first, with the margin, net proceeds
  and a cost status chip when the cost is not complete. The period's figures and one unit's
  figures are one table with a column for each, where they had been two cards of the same
  lines; `getProduct` builds the per-unit lines from the period's lines one for one
  (`service/app/products.py`), so they line up by position. Measured at 1280 px: 336 words to
  170, and 2,999 px to 2,009 px.

Checked with lint, the type check, the production build and screenshots at 390, 768, 900, 1024,
1280 and 1440 px. No page scrolls sideways. The Starter view, which ranks by net proceeds, was
not seen, because the local account is on Growth.

## A37.8 Phase 5, cost entry, built 11 October 2026

- **The upload's stepper.** Choose file, Match columns, Review and Done are named above the
  flow. The stage in use is orange and marked `aria-current="step"`, and a finished stage
  carries a tick. On a phone only the stage in use shows its name. The stage is worked out from
  what the flow already holds, so nothing new is stored or sent.
- **Choose file.** The drop area comes first. The template is a link under it, and what the
  file needs is folded until clicked.
- **Match columns.** The six choices sit two to a row on a larger screen, with a way back to
  choose a different file.
- **Review.** The table has four columns where it had six: the SKU sits under the TikTok
  product and the effective date under the cost, and a matched row carries no sentence. On a
  phone each row is a small block, so nothing scrolls sideways. A replace box is the standard
  check box, where it had drawn as a large square. Back to columns returns to the choices.
- **Typing costs in.** One card with the column names once at the top and a row per variant,
  where each variant had been a card with its own three labels. On a phone the three fields
  share a row with short labels, and each field's full name, with the product, is its
  accessible name. The cost's hint reads 0.00, because 3.40 beside a current cost of £5.00 read
  as a value already entered. Measured: 1,327 px at 1280 where it was 2,699, and 2,389 px at
  390 where it was 4,019.

Checked with lint, the type check, the production build, and a browser run at 1280 and 390 px
against the local copy and a local stand-in for the R2 bucket: a CSV of seven rows reached
Review with three matched, one needing confirmation, one with no match, one invalid cost and
one duplicate, each shown with its status. Apply was not pressed, so the run saved nothing. A
typed cost of "abc" showed its error, marked the field invalid and saved nothing. No page
scrolls sideways.

## A37.9 Phase 6, accessibility and wording, built 11 October 2026

- **Accessibility, as measured.** axe-core 4.10.2 ran its WCAG 2.0 A and AA, WCAG 2.1 AA and
  best-practice rules on 27 shop screens at 1280 and 390 px. It found one fault: Where the money
  went went from its title to a third-level heading. The page now names the calculation at the
  second level for a screen reader, and a second run found nothing on any screen. Pressing Tab
  up to 60 times on Overview, Payouts, Explain this payout, Products, Type your costs, Returns
  and Stock reached no control without a visible focus ring. axe-core does not judge everything
  WCAG asks, so this is a check and not a certificate; no screen reader was used.
- **Returns.** The checked returns are one list, a row each, where each had been a card of five
  lines: 442 words to 349 and 5,716 px to 2,142 px at 1280. A return still to check keeps its
  card, because the card holds its form.
- **Stock.** The four counts sit side by side in one card, under a title that no longer repeats
  Units in hand, and the filter is the compact switch.
- **VAT and tax.** The reserve said twice that it is not tax advice; the page now says it only
  when the service's own estimate, which says so, is not shown. The review date of the tax
  dates is said once when every date was reviewed on the same day.

## A37.4 The phases still to come

Each is shown to the owner before it merges: the Overview (phase 2), Reconcile and Explain this
payout (phase 3), Products (phase 4), cost upload (phase 5), and accessibility and wording
(phase 6). Phase 2 merged in PR 79. Phases 3 to 6 were built on 11 October 2026 (A37.6 to A37.9)
and are one pull request with a commit for each, because the session works on one branch.

## A37.10 Responsiveness and click feedback, built 11 October 2026

The owner approved the audit and structure the same day and asked for all of it in one batch.
Before the change, no control in the app or on the website had a pressed state, a tap on a
phone showed nothing until the next page arrived, and no form told a screen reader it was busy.

- **A press answers within one frame.** A button sinks to 97 per cent and darkens while held. A
  tab, a page link, a switch, a menu item or a payout row takes the orange tint with a 2px
  orange edge. Hover effects that change a background apply only on a device that can hover,
  so a tap on a phone leaves nothing lit. Payout rows and selectable plan cards rise by 2px on
  hover. Every focus ring is now 3px, the width of the app's own rule.
- **A click shows where it is going.** `web/src/components/NavFeedback.jsx` marks a clicked link
  `data-pending`, and the link takes the selected look while the area being left gives it up.
  An orange bar runs along the top of the window when a page takes longer than 120ms, and it
  keeps running while the page's loading skeleton is on the screen.
- **A running action says so.** A button that becomes disabled within 1.5 seconds of its press
  takes `aria-busy` and a small spinner beside its label, and both come off when it is enabled
  again. The buttons that already disable themselves while they work needed no change.
- **Nothing moves after it appears.** The footer was the only shift measured on Pricing and the
  Overview: it showed while a page loaded and was then pushed away. The page now fills the first
  screen, so the footer starts below it.
- **The website serves its own font.** Inter comes from `site/assets/fonts/` (from
  `@fontsource-variable/inter` 5.3.0, under the SIL Open Font License in the same folder), so
  no font service holds up the first paint. The FAQ and the Payout Explainer moved from Space
  Grotesk and IBM Plex Sans to Inter, and their orange and faint grey to the landing page's.
- **The landing images are smaller.** Every image was re-encoded at WebP quality 72, from 868 KB
  to 583 KB in all, and every image below the first screen loads when it is scrolled to.
- **Full prefetching was not added.** The app's links already fetch the next page's frame when
  they come into view and again on hover, in the production build. Fetching the figures too
  would let Next.js show figures up to 300 seconds old (`staleTimes.static` in Next 15.5.27),
  which a finance screen should not do.

Measured on the local copy on 11 October 2026: layout shift 0.000 on 14 app pages and 3 website
pages at 1280 and 390 px, against 0.242 on the Overview and 0.171 on Pricing before; axe-core
clean on all of them; the landing page at 426 KB on first load at 1280 and 332 KB at 390, with
no stylesheet or font from another site. With every page fetch slowed by 700ms, the clicked tab
was lit 20ms after the click, the bar ran from about 190ms, and it finished when the figures
arrived. **Unverified**: the speed of the live sites, because the session's proxy blocks them,
and the feel on a real phone, because only a browser at phone width was used.
