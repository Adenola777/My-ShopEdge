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

Still open: the footer carries no privacy notice or terms, because neither page exists (A14).

The logo is the official artwork from `brand/` (A7): `site/brand/` holds byte-for-byte copies of
`mse-logo-horizontal-notagline.svg`, `mse-mark-colour.svg` and `mse-favicon.svg`, replacing the
hand-drawn bag the supplied page carried. The top bar shows it at 48 px, as the app does.

The page is one static file with its other images inline. It needs no build.
