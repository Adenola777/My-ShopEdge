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

## A37.4 The phases still to come

Each is its own pull request, shown to the owner before it merges: the Overview (phase 2), Reconcile
and Explain this payout (phase 3), Products (phase 4), cost upload (phase 5), and accessibility
and wording (phase 6). Phase 2 waits on the waterfall answer in A37.1.
