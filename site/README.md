# The product website

`index.html` is the public page for MyShopEdge, meant for `myshopedge.inspirecraftglobal.com`.
It was supplied by the owner on 29 September 2026 as `MyShop_Edge___Landing_Page_1.html` and
corrected the same day against the records:

- "Registered with the ICO" is removed, because nothing in this repository records a
  registration. It goes back with its registration number once one is held.
- "12 months of orders" reads "up to 24 months", as A16 rules.
- "The moment you connect" and "instantly" are removed, because a sale counts once TikTok
  settles it (A31.5).
- "Encrypted, end to end" reads "Encrypted in transit", with the token encryption stated.
- "Export or delete" reads "delete", because the data download answers 503 until the storage
  bucket exists.
- The name is written MyShopEdge throughout.
- The email and password panel was a design preview. Email sign-in is off in Neon Auth, so
  Sign in and Get started now go to the app's Start page, which hands off to the provider.

On 30 September the copy was rewritten from `audit/COPY_audit_30_september.md` with the owner's
decisions: the company is written Inspirecraft Global Ltd, as registered, and the address reads
"Maisonette 3". Headlines are sentences, "what you keep" became gross profit, and "Under a
minute" and "Stock and loss update themselves" are gone, because neither was measured or true.

The footer links to the Privacy Policy, the Terms and Conditions and the Cookie Policy, published on 10 October 2026 from the owner's drafts. They live in `web/public/legal/` and are served by the app at `app.myshopedge.inspirecraftglobal.com/legal/`, because that address is known to answer and the Start page needs the same pages (A14).

The logo is the official artwork from `brand/` (A7): `site/brand/` holds byte-for-byte copies of
`mse-logo-horizontal-notagline.svg`, `mse-mark-colour.svg` and `mse-favicon.svg`, replacing the
hand-drawn bag the supplied page carried. The top bar shows it at 48 px, as the app does.

On 10 October 2026 the page was rewritten to the owner's brief of that day, with his approval:
the brief's headings and copy, its section order (hero, problem, product costs, money,
products, exports, returns, VAT and tax, stock, security), a How it works section, and a
Pricing section the navigation links to. Every screenshot is the real app, taken against the
demo shop's made-up data on a local copy, and lives in `shots/` as WebP rather than inline.
Where the brief's copy promised more than the app does, the copy was narrowed:

- "gross profit and margin" reads "gross profit", because no screen shows a margin;
- "notifies you when you reach it" (VAT) reads "shows how much headroom remains", because no
  VAT threshold notice exists;
- "Every export matches the figures" reads that a month summary has the same totals, which
  is the only export the app makes that promise for;
- scheduled exports are said to be on the Pro plan, as `plans.py` lists them;
- cash basis is "by the month TikTok settled it", because the ledger holds the month;
- the tax line adds that Scottish Income Tax rates are not yet included.

The read-only claims stand as before, though A24 records that the minimal TikTok scopes have
never been checked against them.

Revised later on 10 October 2026 after the owner's review of the page:

- The screenshots are retaken on a busier made-up shop. `testdata/generate_payloads.py` gained
  a showcase mode (`MSE_TESTDATA_SHOWCASE=1`) that replaces the August test orders with 235
  ordinary ones settled in six statements, with no unrecognised fee, no unexplained
  adjustment and no reserve, so a visitor sees a working shop rather than the edge cases the
  tests need. `testdata/rows_showcase.json` holds its rows; `load_demo.py` loads it with
  `MSE_ROWS=rows_showcase.json`. The test data itself is unchanged, byte for byte.
- The hero shows one screen at up to 360 px wide, so its figures can be read, instead of two
  at 240 px.
- Below 860 px the links sit behind a menu button, which also carries Sign in.
- How it works follows the problem, so "See how it works" no longer jumps past every feature.
- Product costs shows the cost question and the typing screen, so the Products screen is not
  shown twice.

The page needs no build.
