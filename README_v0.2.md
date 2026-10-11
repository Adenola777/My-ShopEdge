# MyShopEdge v0.3, work in progress

Prepared 21 September 2026, revised 22 September 2026 at 22:00, and brought up to date on
11 October 2026. This package closes the gaps found in the specification audit of the v0.1
drafts dated 20 September 2026, and carries every platform, integration and commercial
decision taken since.

## Where things stand, 11 October 2026

- **The app has a new look.** The owner set the visual system on 11 October (A37): Inter,
  white surfaces, orange only for the primary action and the selected state, status chips
  that carry an icon as well as a colour, and short wording. Every main screen was rebuilt to
  it in four pull requests, 78 to 81, all merged to `main` that day. A37.5 to A37.9 record what
  changed on each screen and how it was checked.
- **Production has not yet picked up PR 81.** Vercel builds production from every merge to
  `main`, and the team's Hobby plan allows 100 deployments a day. That limit was reached on
  11 October, so the merge of PR 81 (`b7e3c50`) did not deploy. Production showed PR 80's build
  (`ba406c3`) when last queried. It deploys once the limit resets, or at once on Vercel Pro.
- **The TikTok Go Live resubmission is ready to send.** TikTok rejected the review on
  7 October. The landing page was rewritten for it, and six screenshots are in
  `design/tiktok_review_11_october/`. The reviewer signs in at
  `https://reviewer.myshopedge.inspirecraftglobal.com/reviewer`, which answered 200 on
  11 October. The reviewer's email and password are sensitive variables on Vercel, which
  never shows them back, so the owner holds them.
- **The demo shop is renamed.** It reads "My TikTok Shop" on the development branch since
  11 October, where it read "Demo shop (sample data)". Staging and production hold no demo
  shop. The demo site runs code from PR 47, so it does not show the A37 design; the owner
  chose on 11 October to leave it so.

## What this repository holds

| Folder | Contents |
|---|---|
| `A2` to `A37` | The rulings, one document per action |
| `schema/` | The consolidated v0.2 schema and migrations 0001 to 0035 |
| `api/` | `openapi.yaml`, 88 operations across 76 paths, 85 schemas, counted 11 October 2026 |
| `service/` | The Python service. FastAPI, psycopg 3, PyJWT |
| `web/` | The Next.js front end, JavaScript with JSDoc |
| `testdata/` | The payload generator, the ingest, and the seeded rows |
| `design/` | The Figma change set, the wireframes, and the TikTok review screenshots of 11 October |
| `admin/` | The admin site (A34), live on Vercel as `myshopedge-admin` |
| `site/` | The landing page, Vercel project `myshopedge-site` |

## Progress by action

| Action | Subject | Status |
|---|---|---|
| 2 | Per-product deductions grid and the Excel ledger | Specified |
| 3 | Every screen from onboarding to account closure | Specified and drawn |
| 4 | Returns, stock and the account | Specified |
| 5 | Daily, weekly and monthly views | Specified |
| 6 | Schema hardening | Specified and applied |
| 7 | Logo integration | Complete. 15 vector files derived from the master |
| 8 | Terminology standard | Specified and applied |
| 9 | Identifiers and reconciliation | Specified and applied |
| 10 | Platform, region and identity | Decided and provisioned |
| 11 | Statement ingestion and scope rulings | Specified |
| 12 | Test data requirements | Built. 119 ledger entries. The ingest did not parse between 142c3dd and 23 September, see A20.8 |
| 13 | Stack and client contract | Decided. Python and JavaScript, no TypeScript |
| 14 | The onboarding screen set | Specified. Corrected 23 September for the real provider |
| 15 | Four screen rulings, the copy pass, VAT | Specified and applied |
| 16 | The six price sheet rows | Specified. Migration 0018 applied to staging and development |
| 17 | Endpoint versions checked against the specification | Settlement detail corrected to finance 202501 |
| 18 | The eight screens the rulings moved | Specified |
| 19 | The first live TikTok calls | Connection proved. The authorised shop is a sandbox shop in region ID, not GB |
| 20 | The real settlement payload, measured | A8 section 3.5 closed. 57 fee fields, 24 shipping, 17 tax. Our maps cover 7, 5 and 1 |
| 21 | The first real British order | Order 576955651451099542 on GBGBLCRKQTEX. A11.2 amended. Section 21.3 corrected by A22 |
| 22 | The unsettled export | Commission measured at 9.00%. Settlement is Delivered plus 8 days. A21.3 corrected |
| 23 | The authorisation flow, from TikTok's page | Seller link is services.tiktokshop.com, not partner. service_id is a third credential. Runbook corrected |
| 24 | Two app paths | The ISV app cannot authorise a production shop until review. A Seller Developer custom app is how the build gets real GB data now |
| 25 | The assumption audit | The provider is Stack Auth signing ES256, not Better Auth signing EdDSA. No handler had ever been invoked. Four new guards |

## Decisions taken, and open to reversal

1. **Product Specification v2.0 is absent from the pack.** The formulas its sections 8 and
   12 were expected to carry are written into the SRD instead, so the pack stands on its
   own. Action 4 carries Return Loss, Contribution and You keep.
2. **Contribution excludes the cost of returned units.** A returned unit's cost appears
   once, either as stock value recovered or as a write-off inside Return Loss.
3. **The brand orange for text and actions is #C4400C**, which measures 5.14:1 on white.
   The v0.1 orange of #F05423 measures 3.5:1 and fails WCAG 2.2 AA for normal-size text,
   which NFR-10 requires. The original orange is kept for large graphics.
4. **Golden dataset numbering.** G10 was already in use for the workbook discrepancy
   dataset. The new datasets are G11, from Action 2, and G12, from Action 4.
5. **Sign-in pages are hosted by the identity provider.** Settled by Action 10, corrected
   23 September 2026, then corrected again the same evening because the first correction
   was wrong. The provider is **Stack Auth**, which is what the project's own Neon Auth
   configuration says and what A14 originally stated. Tokens are signed **ES256** over
   P-256, verified by fetching the provider's JWKS, and carry `email`,
   `emailVerified`, `name` and `role` among their claims. Issuer and audience are both the
   origin of the Neon Auth URL. **There is no second factor and none can be added**, which
   A14 section 14.7 sets out.
6. **The database is Neon, in London.** Action 10. Plain PostgreSQL 16 with the four
   hand-rolled roles and FORCE row level security applying verbatim.
7. **Bank reconciliation is out of scope.** Action 11, against PRD 6.2. The consequence is
   that `settlements.settlement_reference` has no automatic source.
8. **The TikTok invoice stays**, as an identifier for reconciliation. The VAT reclaim
   wording comes off the screen, because PRD 6.2 excludes VAT accounting for registered
   sellers.
9. **Where TikTok and a seller's own document disagree, TikTok is taken as correct.**
10. **Cost files are Excel and CSV only.** A15.1. Word and PDF carry no columns, so reading
    a cost from one means guessing, and a wrong cost is worse than a missing one.
11. **The three prices are exclusive of VAT, and no VAT is charged.** A15.6. On 30 September
    2026 the owner ruled that Inspirecraft Global Ltd is not VAT registered, so a seller pays
    £9.99, £24.99 or £49.99 and nothing more. The rest of this item is kept as it was written. Starter, Growth and Pro are £9.99,
    £24.99 and £49.99 plus VAT. Stripe prices are immutable once created, so
    `tax_behavior: "exclusive"` had to be right first time. It was. The three prices were
    created in the live account on 23 September 2026 and each one reads back as GBP,
    recurring monthly, and exclusive.
12. **History is twenty-four months on every plan**, not tiered. A16.2. Whether TikTok
    exposes two years of statements is unverified. It was tested on 23 September and the
    test answered nothing, because the shop had no trading history. Only a shop that has
    been trading for over two years can answer it, so connecting any shop is not enough.
13. **The order limit is enforced softly.** A16.3. The count is shown at eighty per cent
    and at a hundred, the larger plan is offered, and nothing stops. No month closes, no
    export is withheld, no figure stops updating.
14. **The plans differ by what they include**, ruled 10 October 2026 (A35). Starter shows what
    TikTok Shop left the seller and no profit. Growth adds product costs, gross profit and
    margin, the orders behind each figure, exports and the cash basis. Pro adds scheduled
    exports, the list of recent export files and the statements needing review. The service
    enforces it from the plan Stripe reports, and an account with no live plan keeps
    everything. A seller can change plan in the app; that call is unverified against Stripe.
15. **No figures before a trial starts**, ruled 10 October 2026 (A36), which replaces the "no
    live plan keeps everything" of item 14. A shop with no trial is read for 30 days, then no
    more. An ended plan reads but cannot change or export anything. A36 also records the
    owner's rulings on the brief's navigation, net sales, gross profit so far, colours and
    payout statuses, and the build order that follows.
16. **The visual system**, ruled 11 October 2026 (A37). Inter for text and figures, no
    gradient outside the logo, white page, navigation and cards, orange only for the primary
    action, the selected state and key emphasis, and status chips with an icon as well as a
    colour. Every amount is dark and a deduction carries its minus sign; red is kept for stock
    written off and a failed payment, and a payout difference nobody has explained is amber.
    Each TikTok fee keeps its own line. Explanations on the app's screens are short phrases,
    which relaxes the house style for those screens only.

## Open items, by owner

| Item | Owner | Blocks |
|---|---|---|
| TikTok app developer approval | **Granted 23 September 09:00** | Four categories, all UK: Finance and Accounting, ERP, Order Management, Product Information Management |
| A Seller Developer custom app on `GBGBLCRKQTEX` | Adenola | Every claim the ingestion makes. The ISV app cannot authorise a production shop before review, see A24. Needs `TIKTOK_SERVICE_ID`, `TIKTOK_APP_KEY` and `TIKTOK_APP_SECRET` |
| Whether TikTok exposes twenty-four months of statements | **Still open after 23 September.** The call was made and returned nothing, against a shop with no trading history, so it answered nothing. Needs a shop trading over two years. See A19.3 | Whether A16.2 can be delivered |
| Whether the TikTok invoice number is reachable from Seller Center | Adenola | Reconciliation identifier |
| The literal column labels on a settlement export | **Closed 23 September.** Measured from a real payload. See A20 | A8 section 3.5 |
| Which Neon project the product runs on | **Settled 23 September** | `super-mouse-64697125`, the direct Neon account. See below |
| Applying migrations 0017 and 0018 | Adenola | Nothing blocks it now the project is settled |
| Repository access for `Adenola777/My-ShopEdge` | **Closed.** Work is pushed and merged through pull requests | Nothing |
| The TikTok Go Live resubmission | Adenola | Real sellers connecting through the app. The screenshots and reviewer link are ready, see above |
| Vercel's Hobby limit of 100 deployments a day | Commercial | Production deploying PR 81 on 11 October. Pro removes the limit |
| Whether `tiktok_payments` amounts are pounds or pence | Claude, after the sync of 12 October at 05:47 UTC | Unmatched payouts (A36 item 6) showing the right amount |
| Postmark: a server, `POSTMARK_SERVER_TOKEN` on Render, and the domain's DNS records | Adenola | Notice emails |
| The five R2 variables on `My-ShopEdge-1`, and `DATABASE_URL` with them on `My-ShopEdge-erase` | Adenola | Cost uploads, exports, and erasing closed accounts |
| Whether the shops move to adenola.adegbesan@gmail.com | Adenola | Nothing technical |
| Backup retention, capped at six hours on the current Neon plan | Commercial | Nothing yet |
| Immutable storage for the invoice documents | Deferred, see A10.8 | Nothing yet |
| A Vercel blob store named `myshopedge-seller-files`, provenance unknown | Identify or remove | Nothing yet |
| Whether Vercel `lhr1` guarantees data at rest in London | Confirm before launch | Data protection alignment |
| Where Stack Auth processes identity data | Confirm before launch | Data protection alignment. `api.stack-auth.com` is not a Neon host |
| Whether single factor authentication is acceptable at launch | Commercial and risk | Nothing technical. A14 section 14.7 |
| Where the Python service is hosted | **Settled 24 September.** Render, Frankfurt, for the MVP, with a move to a UK host later | Nothing now |
| Emergent AI's work in `Adenola777/MYSHOPEDGE` | Adenola | Approved for porting on 28 September. The copy step needs a permission the session's safety check refused. See `audit/EMERGENT_review_28_september.md` |

## The Vercel, GitHub and Neon wiring

Traced 23 September 2026, because two Neon projects were in play and only one held the work.

| Piece | Value |
|---|---|
| GitHub | `Adenola777/My-ShopEdge`. Vercel is wired to this one, not to `MyShopEdge-` |
| Vercel team | `coterie448-8267's projects`, `team_H7VQC0OWq6IaOif0bUtyZlgg` |
| Vercel project | `my-shop-edge`, `prj_r4jxHJm7Pw4dJxYmN9RyRV7grwvg`. Framework nextjs, root `web`, functions in `lhr1` |
| Database | `super-mouse-64697125`, London, in the Neon account under adenola.adegbesan@gmail.com |

**The trap to avoid.** A Neon project provisioned through the Vercel Marketplace lives in a
Neon organisation that Vercel creates and manages, tied to the Vercel login rather than to
the Neon account you sign into at neon.com. That is what `holy-glitter-85206770` is, and it
is why an API key from the direct account cannot see it. It held no schema of ours, and
`DATABASE_URL` on the Vercel project pointed at it.

The product runs on the direct account's project, because that is where twenty migrations,
three branches, the seeded seller and the verified row level security live.

**The convenience is kept, by using the other integration.** Ruled 23 September 2026. Neon
offers three ways to connect to Vercel, not two. The Vercel-managed one provisions a new
database under Vercel. The **Neon-managed** one, installed from the Neon console and listed
in the Vercel Marketplace under Connectable Accounts, connects a project that already
exists and still injects the variables automatically and still creates a database branch
per preview deployment. Its branch cleanup follows git branches rather than deployments,
which is the better of the two.

So `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, the legacy `PG*` variables and
`NEON_AUTH_BASE_URL` are all set automatically, on a project holding the work. **The two
integrations cannot coexist on one Vercel project**, so the Vercel-managed one is removed
first.

**None of this is urgent, and it was treated as though it were.** Checked 23 September:
the Next.js front end never touches the database. It calls the API over HTTP through
`NEXT_PUBLIC_API_BASE_URL` and contains no Postgres client, no Neon package and no
reference to `DATABASE_URL`. The database belongs to the Python service, which is not
hosted on Vercel and has no host decided yet.

So the stale `DATABASE_URL` entries left on the Vercel project by the marketplace
integration are inert. Nothing reads them. They can stay until the integration is sorted
out at leisure. The one variable the Vercel project will need is
`NEXT_PUBLIC_API_BASE_URL`, and that waits on the service having somewhere to run.

**Where the Python service runs is an open item nobody has raised.** Vercel is hosting the
front end. FastAPI, psycopg and a connection pool are a different shape of deployment, and
choosing its home also decides where `DATABASE_URL` lives.

`NEON_AUTH_BASE_URL` is the variable the service already falls back to. With it present,
the JWKS URL, the issuer and the audience are all derived and nothing has to be set by
hand. The issuer and audience are the origin of that URL with no path, which is why the
service derives them with `urlsplit` rather than by appending to the base.

## Counts

| Measure | v0.1 | v0.3 |
|---|---|---|
| Functional requirements | 73 | 87 |
| Of which Must | 64 | 78 |
| Test cases | 84 | 107 |
| Golden datasets | 10 | 12 |
| Screens ruled | 15 | 36 live, 38 defined, 2 cut by A15. See `SCREENS.md` |
| Screens drawn in Figma | 0 | 18 |
| Schema migrations | 0 | 35, through 0035 |
| API operations specified | 0 | 88 |

## Build status

The specification is nearly complete, and the application is built and running against real
shops. The rows below were brought up to date on 11 October 2026; CLAUDE.md carries the detail.

| Layer | State |
|---|---|
| Brand, terminology, screen specification, data model, API contract | Done |
| Schema applied | Through 0035 on all three branches, with 36 migrations recorded on each, queried on 11 October 2026. 0024 and 0029 closed the Neon Data API exposure that CLAUDE.md describes |
| Backend | The contract holds 88 operations across 76 paths. See CLAUDE.md for what is served |
| Authentication | Verified by a real sign-in on 24 September. Issuer and audience were read from that token and set on Render, and the first production account was created from it |
| Billing | Screens built. The three products and prices were created in the live Stripe account on 23 September. See CLAUDE.md for the identifiers. Since 10 October each plan's features are enforced by the service (A35), and a running plan can be changed from the app |
| TikTok integration | Three real shops on production, as CLAUDE.md records: IkonetU and My ShopEdge since 29 September, and LivaHome since 7 October. A daily cron job on Render reads orders, returns, finance and inventory, and a token refresh has reached TikTok |
| Front end | All 36 screens built on 29 September, and rebuilt to the A37 visual system on 11 October 2026. axe-core found no accessibility fault on 27 shop screens at 1280 and 390 px after that work. See `SCREENS.md` and A37 |
| Deployment | The front end is live on Vercel production at `app.myshopedge.inspirecraftglobal.com`. The Python service runs on Render as `My-ShopEdge-1` in Frankfurt, deploying `main`, since 24 September. The demo service `My-ShopEdge-demo` is kept awake by the `keep-demo-awake` workflow, whose run at 13:09 UTC on 11 October passed; its nine runs so far came hours apart, not every ten minutes |
| Tests | CI runs nine service test files (auth, contract conformance, handler smoke cases, the London business date, cost files, tax set-aside, insights and trends, the TikTok client and the Data API guard) with ruff and pip-audit, and lint, the type check, an audit and a build for `web` and `admin` |

## Scope check

Every screen added in Action 3, S16 to S32, was tested against PRD section 6.1 and maps to
an epic that is in the MVP. Nothing added in Actions 2 to 16 falls inside PRD 6.2, with
three exceptions ruled on above: bank reconciliation, which has been withdrawn, the VAT
reclaim wording, which has been removed while the invoice identifier is kept, and four
price sheet rows ruled out of the MVP in A16.
