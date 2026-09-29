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

Still open: the footer carries no privacy notice or terms, because neither page exists (A14),
and the address line reads "Massionette 3" exactly as supplied.

The page is one static file with its images inline. It needs no build.
