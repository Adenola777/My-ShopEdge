# Copy audit, 30 September 2026

The owner asked for every word a customer reads to be audited, from the landing page to the
last screen, so that MyShopEdge reads as a premium product rather than as a hurried build.

**Method.** Every string a customer can see was extracted from `site/index.html` (83 lines)
and from `web/src` (about 700 strings across 45 screens and components), and each one was
read against the voice below. Claims were checked against the code before being called
false: the plan list in `service/app/plans.py`, the callback page, and the company name as
it appears in the rulings. Nothing in this document has been changed in the product yet.

## The voice

A premium finance product earns trust by being exact, calm and brief. These rules sit on
top of the owner's house style in CLAUDE.md, and where they differ, the house style wins.

1. **Speak to the seller about their business, never about our machinery.** No customer
   should ever read "service", "deployment", "configured", "Stack", "tokens", "ledger
   entries", "JSON", "YYYY-MM" or a raw status such as `past_due`.
2. **Every sentence carries a subject and a verb** (house style). Headlines are short
   sentences, not fragments. "Your numbers. Your control." becomes a sentence.
3. **Promise only what the product does today.** A feature that is not built is not named,
   and a figure that is not loaded is not implied.
4. **One word for one idea, everywhere.** The terms table below fixes them.
5. **When something goes wrong, say what happened, what it means for the seller's money,
   and what to do.** In that order, in two sentences at most.
6. **Quiet confidence.** No "smarter", "fantastic", "seamless", "powerful" or exclamation
   marks. The figures are the selling point.
7. **British English**, sentence case for headings, and "for example" rather than "e.g.".

## Findings, most serious first

### 1. Internal and developer language shown to customers

These are the lines that most make the product read as unfinished. Each would reach a real
seller in the situation described.

| Where | Today | Proposed |
|---|---|---|
| `(site)/start/page.jsx`, `(site)/handler/[...stack]/page.jsx` | Sign-in is not set up on this copy of MyShopEdge. The Stack project id is not configured here, so nobody can sign in yet. | Sign-in is temporarily unavailable. Please try again shortly. |
| `connections/tiktok/callback/page.jsx`, `ConnectTikTok.jsx` | Connecting a TikTok Shop is not switched on yet. The TikTok app details are not set on the service, so nothing was connected. | We could not connect your shop just now. Nothing has changed, and you can try again in a few minutes. |
| `connections/tiktok/callback/page.jsx` | The key that protects your TikTok access is not set on the service, so nothing was stored. | The same wording as the line above. |
| `billing/PaymentForm.jsx` | Card payments are not set up yet. | Card payments are temporarily unavailable. Nothing has been charged. |
| `billing/payment-failed/page.jsx` | Changing the card from MyShopEdge is not built yet. | To update your card, contact us at info@inspirecraftglobal.com and we will send you a secure link. *(Only if the owner agrees to handle it by email until self-service exists.)* |
| `tax/page.jsx` | The VAT registration threshold is not loaded on this deployment yet, so your position against it cannot be shown. | Your VAT position will appear here shortly. We are adding this year's HMRC threshold. |
| `tax/page.jsx` | Tax dates are not configured on this deployment yet. | Your key tax dates will appear here shortly. |
| `glossary/page.jsx` | No rules are loaded yet. Reference rules appear here once they are configured. | This page is being prepared. |
| `setup/page.jsx` | Stopped on ${failedDomain.domain} (shows `orders`, `returns` or `finance`) | Reading paused at your orders / returns / payments, named in words. |
| `billing/page.jsx`, `billing/confirmed/page.jsx` | Your subscription is ${status} (shows `past_due`, `incomplete`) | One written sentence per status, for example "Your last payment did not go through." |
| `settings/data/page.jsx` | Each table comes as a JSON file and a CSV file ... Your stored TikTok tokens are left out, because they are secrets. | Your download holds each part of your records as a spreadsheet file. Your TikTok sign-in details are never included. |
| `products/[productId]/transactions/page.jsx` | These are the ledger entries that add up to the figures on the product screen. | These are the transactions behind this product's figures. |
| `SettingsForms.jsx` | Absorption tolerance (units). Above this, an unexplained rise in TikTok stock is raised as a discrepancy rather than absorbed quietly. | Stock rise to accept without asking (units). A larger unexplained rise in TikTok's count is flagged for you to check. |
| `SettingsForms.jsx` | Enter the month as YYYY-MM, for example 2026-06. | A month picker, so no format is typed. |
| `ApiProblem.jsx` | MyShopEdge answered with an error, so no figures are shown rather than wrong ones. | We could not load your figures just now. We show nothing rather than risk showing a wrong number. Please try again in a moment. |
| `ApiProblem.jsx` | The request for ${what} did not reach MyShopEdge. / took too long, so nothing is shown rather than part of it. | We could not load ${what} just now. Please try again in a moment. |

### 2. Statements that are no longer true, or not yet true

| Where | Today | Why it is wrong | Proposed |
|---|---|---|---|
| `connections/tiktok/callback/page.jsx` line 123 | Reading your orders, returns and statements is not switched on yet, so no figures appear until it is. | The sync has run against two real shops since 29 September. | Your shop is connected. We are reading your orders, returns and payments now, and your figures fill in as they arrive. |
| `service/app/plans.py` line 88, Pro | Scheduled exports | Nothing schedules an export. Exports are built on request only. | Remove until built. |
| `plans.py` lines 72 and 89 | Priority support | No support system or response commitment exists. | Remove, or replace with a promise the owner can keep, such as "Email support from the founding team". |
| `billing/page.jsx` line 86 | Most chosen | No seller has chosen a plan yet, so the claim cannot be true. | "Recommended". |
| Landing page | Under a minute. | Not measured. | Remove the timing, or measure it first. |
| Landing page | How close you are to the VAT threshold, months ahead. / Set aside tax without doing the maths. | The tax figures show nothing until the HMRC reference values are loaded (CLAUDE.md, blocked table). | Keep only once the reference rules are loaded. |
| Landing page | Stock and loss update themselves. | Stock updates when the seller checks each return, not by itself. | You mark each return as resellable or not, and your stock and write-offs follow. |

### 3. The company name is spelt two ways

`site/index.html` writes **InspireCraft Global Limited** three times. `web/src/app/layout.jsx`
writes **Inspirecraft Global Limited**, as CLAUDE.md does. The registered form at Companies
House was not checked, because this session cannot reach it. The landing page footer also
reads **Massionette 3**, which may be a misspelling of Maisonette. **Both need the owner's
confirmation.**

### 4. House style: fragments where sentences belong

The landing page carries most of these. Tables and button labels are exempt, because a label
names a thing rather than making a statement.

| Today | Proposed |
|---|---|
| Smarter finance for social commerce. | See what your TikTok Shop really earns. |
| Sell → Track → Grow | Remove. It says nothing the page does not say better. |
| Your numbers. Your control. | Your figures stay yours. |
| Read-only, always | MyShopEdge can read your shop, and it can never change it. |
| Three steps. No spreadsheets. | You are set up in three steps. |
| Every fee, named. Nothing buried. | Every fee TikTok takes is named and totalled. |
| Returns, handled properly. | Each return is checked and counted once. |
| Know your best (and worst) sellers. | See which products earn you the most, and which cost you. |
| Connect once. See what you keep. No spreadsheets. | Connect your shop once, and MyShopEdge keeps your figures current. |
| Financial clarity for TikTok Shop sellers. | Bookkeeping built for UK TikTok Shop sellers. |

### 5. One word for one idea

The same thing is called different names on different screens. The first column is the
proposed single term.

| Use | Instead of | Where the others appear |
|---|---|---|
| **Gross profit** | "what you keep", "kept", "gross profit after returns" | Landing uses "keep", the app uses "gross profit after returns". Keep "after returns" in the one line that defines it. |
| **Payout** | "paid out", "settlement", "statement" | Today, Money, the callback page. "Settlement" stays only in "Cash basis counts money in the month TikTok settled it." |
| **Update** | "sync", "read", "brought up to date", "first sync" | Top bar, Today, Stock, Setup. |
| **Product** and **variant** | "SKU", "seller SKU", "product variant" | Stock, costs. Say "SKU" only where the seller types their own code. |
| **Needs attention** | "Needs you", "What needs your attention" | Today, notifications. |
| **Mismatch** | "Discrepancies", "A figure differs" | Screen title and nav. |
| **Connect** | "authorise", "approve", "link" | Connect pages and landing. Use "approve" only for the step on TikTok's own page. |
| **for example** | "e.g." | `CostForm.jsx`. |

### 6. Wording that reads as unsure or odd

| Where | Today | Proposed |
|---|---|---|
| `discrepancies/page.jsx` | TikTok charged a fee under a name MyShopEdge does not recognise. You have done nothing wrong, and the money is counted in full. | TikTok charged a fee we have not seen before. It is included in your figures in full, and we are identifying it. |
| `discrepancies/page.jsx` | Totals use TikTok's value while this is open . Your value is kept beside it. | Your totals use TikTok's figure until this is resolved. Your own figure is kept alongside. *(Also removes the stray space before the full stop.)* |
| `connection-problem/page.jsx` | Put it right | Reconnect your shop |
| `connection-problem/page.jsx`, `SettingsForms.jsx`, `settings/disconnect/page.jsx` | reconnecting the same shop resumes against them | Reconnect the same shop at any time and everything continues from where it stopped. |
| `NotificationActions.jsx`, `ResolveActions.jsx` | That did not go through. | That was not saved. Please try again. |
| `billing/confirmed/page.jsx` | Banks refuse for ordinary reasons, and trying again usually works. | Banks sometimes decline a first check. Trying again, or using another card, normally resolves it. |
| `glossary/page.jsx` versus the navigation | The page is titled Glossary and describes "the rules MyShopEdge uses"; the navigation promises "What each figure and word means". | Make the page a true glossary of the product's terms, with the reference rules below it. |
| `layout.jsx` footer | Figures are drawn from your own shop data and are not financial advice. | Your figures come from your own shop data. They are not financial advice. |

## What is already good

Much of the app already speaks well, and these lines set the standard for the rest:

- "Without costs you see what is left after TikTok. With costs you see what you keep."
- "This changes your count in MyShopEdge only. TikTok's own figure stays as it is."
- "We store no card details. Stripe holds them and we hold a reference."
- "Days of cover is stock on hand divided by the daily rate of the last fourteen days."
- The deletion screen, which states plainly what stops, what is erased and what is kept.

## Decisions for the owner

1. **The company name:** InspireCraft or Inspirecraft, as registered, and the footer address.
2. **The plan list:** remove Scheduled exports and Priority support, or say what support is
   offered.
3. **"Most chosen"** becomes "Recommended".
4. **The single terms** in section 5, above all "gross profit" rather than "what you keep".
5. **Card changes:** whether sellers email you until self-service exists.

Once these are decided, the changes are one pass through the files named above, followed by
a screenshot of every screen at phone and desktop widths.

## The owner's answers, 30 September 2026

1. The company is **Inspirecraft Global Ltd**, and the address reads **Maisonette 3**.
2. The plan list stays as it is, Scheduled exports and Priority support included. The owner
   ruled that the product offer is delivered as the build continues.
3. "Most chosen" stays.
4. **Gross profit** replaces "what you keep". The A8 label "Gross profit after returns" stays
   where the figure is defined, because A8 and CLR-5 set it.
5. Until the app can change a card, a seller emails info@inspirecraftglobal.com.

The rewrite then went through every file named in sections 1, 2, 4 and 6. The landing page's
tax card stays, as part of the offer. The glossary now opens with the figures' meanings, taken
from A8, above the tax rules. Section 5's other single terms are not applied, because only
gross profit was decided.
