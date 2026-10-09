# Copy audit status, Area A, 9 October 2026

This file records where each Major and Minor finding of Area A in `audit/COPY_audit_8_october.md` stands on 9 October 2026. Area A covers onboarding, account, billing and the shell. The owner approved fixing every Major and Minor finding on 9 October. The twelve Blocking rows are left alone, as the brief says, and so are Areas B, C and D.

Each row was checked against the current file rather than against the audit's line numbers, because copy batches 1 to 3, cancel and change card, the first read on connection, the export lists and the loading and error pages had moved the code on since 8 October. Every claim added by this change was checked against the code or the contract first. The checks named at the end were run after the changes. No screen was driven in a browser for this change, so the new states are checked by lint, type check and build only.

## Counts

| Status | Rows |
|---|---|
| Already fixed | 45 |
| Fixed now | 38 |
| Kept | 2 |
| Owner decision | 7 |
| Needs building | 1 |
| Needs Area D | 1 |
| **Total** | **94** (29 Major, 65 Minor) |

## Findings

The "Audit line" column is the row's line in `audit/COPY_audit_8_october.md`. Paths are under `web/src` unless they start with `service/`.

| Audit line | Screen | Current text (short) | Severity | Status | What was done, or why |
|---|---|---|---|---|---|
| 136 | S2 First sync | "This card shows each part as it arrives." | Major | Already fixed | `SyncProgress.jsx` no longer promises a notification, and the card now says only what it shows. |
| 137 | S33 plan cards | "Suggested" | Major | Fixed now | The flag "Most chosen" rested on no sign-up data, so `PaymentForm.jsx` now reads "Suggested", which is what the hard-coded highlight is. |
| 138 | S33 plan cards (service) | "Growth covers a shop taking up to 500 orders a month." | Major | Already fixed | The straplines in `service/app/plans.py` are now full sentences, after Area D's copy batch. |
| 139 | S33 plan cards (service) | "One TikTok Shop connection" | Major | Owner decision | Whether Starter allows one shop is one of the owner's open decisions, so the line is unchanged. |
| 140 | S33 plan cards (service) | "Everything in Starter" / "Exports on a sales basis or a cash basis" | Minor | Owner decision | What Growth and Pro hold back is an open owner decision, and no plan gating exists, so the lists are unchanged. |
| 141 | S33 plan cards | "Made for up to {n} orders a month. Nothing stops if you sell more." | Minor | Already fixed | The limit now reads as a guide, which matches the soft limit ruled in A16.3. |
| 142 | S33 plan cards (service) | "VAT threshold tracking and set-aside guidance" | Minor | Needs Area D | The text is a service string in `service/app/plans.py`, and A8.4 names the term "VAT registration threshold", so Area D owns the change. |
| 143 | S33 plan step | "Continue with {plan}" and "Your plan is fixed once you continue to the card." | Major | Already fixed | The button names the plan, and the summary says the plan is fixed at the card step. |
| 144 | S33 plan step | "Setting up your trial" | Minor | Already fixed | The busy label says what is happening. |
| 145 | S33 plan error | `data?.detail ?? "We could not start the trial. Nobody has been charged. ..."` | Major | Already fixed | Every refusal `start_trial` can give (`service/app/billing.py`) now says in its own detail that nothing was charged or started, so the detail no longer drops the reassurance. |
| 146 | S33 card error | "{message} Nothing has been charged. Check the details or try another card." | Major | Already fixed | The card error says what was charged and what to do next. |
| 147 | S33 card step | "Your {n} free days run until {date}." | Minor | Fixed now | The plan summary no longer repeats "nothing is charged today", so the reassurance appears once at the top and once beside the button. |
| 148 | S33 trial date | `{trialEnds}` | Minor | Fixed now | The estimate is now worked out in London time with the year, and once Stripe creates the subscription the screen shows the `trial_ends_at` Stripe returned. |
| 149 | S33 done | "Go to your shop" | Minor | Already fixed | The label no longer names a dashboard, and `/shops` resumes the seller at the right step. |
| 150 | S33 current plan, ended | "Your plan has ended. Choose a plan to start again." | Major | Fixed now | `start_trial` refuses only a live plan, so `/billing` now shows the plans to a seller whose plan ended, under that heading, rather than a dead end. |
| 151 | S33 current plan, past due | "Your figures stay open to you while it is sorted." | Minor | Already fixed | The past-due state no longer says there is nothing to do. This change also adds a "Use a different card" link to `/billing/card`, which accepts a past-due plan. |
| 152 | S33 page title | "Your plan" | Minor | Already fixed | The page title fits every state. |
| 153 | S33 plans error | "Try again" | Minor | Already fixed | The plans error has a retry button. |
| 154 | S34 Confirmed title | "Card confirmed" | Major | Already fixed | The title no longer says a payment was taken. |
| 155 | S34 Confirmed button | "Go to your shop" | Minor | Already fixed | The button says where it goes. |
| 156 | S34 failed | "See what to do next" (past due) / "Try the card again" | Major | Already fixed | A past-due seller is sent to `/billing/payment-failed`, so the loop is gone. |
| 157 | S34 nothing waiting | "See your plan" / "Choose a plan" | Minor | Fixed now | A seller with a plan is sent to Profile and plan, and a seller with none is sent to choose one, each with a label that says so. |
| 158 | S38 Payment failed | "...for your {Plan} plan." | Minor | Already fixed | The slug is mapped to the plan name, and a missing plan reads "your plan". |
| 159 | S38 Payment failed | (sentence removed) | Minor | Already fixed | The guess about a cautious bank is gone. |
| 160 | S38 Payment failed | "Use a different card" | Major | Already fixed | The email route is replaced by `/billing/card`, which `startCardChange` and `setCard` back. |
| 161 | S38 Payment failed | (no retry date) | Major | Needs building | Nothing reads Stripe's retry schedule or the date a plan ends after failed retries, so the screen cannot state either. That needs the service to read and serve both from Stripe. |
| 162 | S17 Start | "...sign in with Google, GitHub or Microsoft." | Major | Owner decision | The page's own note says three providers were on on 24 September, and CLAUDE.md says Google only on 7 October. The Stack configuration cannot be read from this session, so the owner needs to confirm the list before the sentence changes. |
| 163 | S17 Start | "...reads your orders, returns and statements." | Minor | Owner decision | The name for payouts and statements waits on the owner's ruling between A8.4 and A29.7. |
| 164 | S17 unconfigured | "Sign-in is not working at the moment." + "Try again" | Minor | Already fixed | The error says nothing changed and offers a retry. |
| 165 | Handler | "Sign in" / "Create an account" / "Sign out" | Minor | Already fixed | Each Stack route has its own title. |
| 166 | S37 Signed out | "You are signed out" | Minor | Fixed now | `afterSignOut` in `lib/stack.js` now points to `/signed-out`, so a deliberate sign-out reaches its confirmation. |
| 167 | S37 / ApiProblem | "Your session has ended" | Minor | Already fixed | Both screens now use "Your session has ended". |
| 168 | S36 Email in use | "Sign out and sign in again" | Minor | Already fixed | The button names the next step. |
| 169 | Closing | "Your account details could not be loaded." | Minor | Already fixed | The heading no longer claims the service was unreachable when it answered with an error. |
| 170 | Closing | "After {date} your name and email are erased..." | Major | Owner decision | The erase job needs variables on Render that only the owner can set, and the deletion wording is an open owner decision, so the text is unchanged. |
| 171 | Closing | "Your shops stay disconnected, so you would connect each one again on TikTok." | Minor | Already fixed | The sentence now says what happens if the seller keeps the account. |
| 172 | TikTok callback | "Your shop connection" | Minor | Already fixed | The title describes the outcome. |
| 173 | Callback, unsupported | "MyShopEdge does not read this shop, so no figures will appear for it." | Major | Fixed now | The button was already there. The added sentence is backed by `connections.py`, which starts no read for a rejected shop, and by `shops_due_for_sync`, which reads GB shops only. |
| 174 | Callback, unsupported | "MyShopEdge does not read this kind of shop." | Minor | Already fixed | The word "yet" is gone. |
| 175 | Callback, success | "MyShopEdge only reads your shop and never changes it." | Minor | Already fixed | The sentence describes what the code does rather than the token's scopes. |
| 176 | Callback, success | "See your shop being read" | Minor | Kept | Since 8 October `tiktok_callback` starts the first read straight away (`connections.py`, `_first_sync`), so the label is now true. |
| 177 | Callback, errors | "Connect again" (to /shops/connect) / "Start again" | Minor | Fixed now | `Problem` now takes a link, and the callback sends a seller who already has a shop to `/shops/connect` with "Connect again". |
| 178 | Callback, fallback | "The shop could not be connected." + "Nothing has changed. Start again in a few minutes." | Minor | Already fixed | The fallback no longer shows the raw detail. |
| 179 | S1 Connect | "MyShopEdge reads your shop and never changes anything in it." | Minor | Already fixed | The fragment is now a sentence on both pages. |
| 180 | S1 Connect | "We read only what we need to work out what you earned." | Minor | Already fixed | The fragment is now a sentence. |
| 181 | S1 Connect | "Payments and fees" | Minor | Owner decision | The one name for payouts waits on the owner's ruling between A8.4 and A29.7. |
| 182 | Your shops list | "United Kingdom" | Minor | Already fixed | GB is shown in words. |
| 183 | Shell: Your shops | "Your shops" (to `/shops?all=1`) | Major | Fixed now | `/shops?all=1` lists the shops even when there is one, and the top bar and Settings link there, so the link no longer returns a one-shop seller to where they were. |
| 184 | ConnectTikTok | "The connection could not be started. Nothing has changed. Try again in a moment." | Minor | Already fixed | The fallback gives a next step. |
| 185 | S2 First sync | "Could not be read" + retry note / "Reconnect your shop" | Major | Already fixed | A failed part says it is tried at the next daily read, and a part needing reconnection links to the connection page. |
| 186 | S2 First sync | ". This is out of date." | Minor | Already fixed | The fragment is a sentence. |
| 187 | S2 First sync | "Other shop data" | Minor | Already fixed | An unknown domain no longer shows its code. |
| 188 | S2 First sync | "Waiting to try again" | Minor | Already fixed | The vague "shortly" is gone. |
| 189 | S35 Continue setting up | "See your shop's progress" / "Choose a plan" / "Add product costs" / "Tell us about your business" | Major | Fixed now | Each step now carries its own button label, in place of "Continue: {label}". |
| 190 | S35 step names | "Connect your shop" / "Read your shop's history" / "Choose a plan" / "Add product costs" / "Tell us about your business" | Minor | Fixed now | Every step name now has the same form. |
| 191 | S35 sync note | "Stopped while reading your {part}. MyShopEdge tries again at the next daily read." | Minor | Fixed now | "Paused" is replaced, and a part that needs reconnecting says "Reconnect your shop to carry on" because the daily read does not retry it. |
| 192 | S35 plan step | "Not known" | Minor | Fixed now | A failed subscription or tax request now reads "Not known" and is not offered as the next step, so a paying seller is not sent to the plans. |
| 193 | S35 costs note | "{n} of {m} products have a cost" | Minor | Fixed now | The count is pluralised and uses "products", the noun S20 uses. |
| 194 | S3 Costs choice | "Without costs you see your net proceeds. ..." | Major | Fixed now | "What is left after TikTok" is replaced by Net proceeds, as A8.4 rules. |
| 195 | S3 Costs choice | "Costs are optional, and you can add them later." | Minor | Fixed now | The fragment is a sentence. |
| 196 | S3 Costs choice | "Skip costs for now" | Minor | Fixed now | The button says what it does. |
| 197 | S4 Upload | "Upload your costs" / "Choose your Excel or CSV file. ..." | Major | Fixed now | The heading now fits the screen a seller arrives on. |
| 198 | S4 Upload | "...is kept as the record behind your costs. MyShopEdge does not share it." | Minor | Fixed now | "Nobody else can open it" overstated it. No operation lets the seller download the file, so the audit's "Only your account can download it" would also have been untrue. |
| 199 | S4 Upload, storage error | "Files cannot be uploaded or downloaded just now. Nothing you saved has been lost. ..." | Major | Already fixed | `service/app/storage.py` no longer names the deployment, after copy batch 1. |
| 200 | S4 Upload, error | "Your file did not upload, so nothing was read. Check your connection and choose the file again." | Minor | Fixed now | "File store" is gone, and the message gives a next step. |
| 201 | S4 Upload | "Uploading and reading your file." | Major | Fixed now | A status line now shows while the file uploads and is read. |
| 202 | S4 Upload | "Which column is which" | Minor | Fixed now | "Column mapping" is replaced. |
| 203 | S4 Upload | "Apply 1 cost" / "Applying" | Minor | Fixed now | The label is pluralised and changes while the costs are applied. |
| 204 | S4 Upload | `x.reason ?? OUTCOME_WORDS[x.outcome]` | Minor | Fixed now | A row with no reason from the service shows words, never the outcome code. |
| 205 | S4 Upload, done | "Continue to your business details" | Minor | Fixed now | The button says where it goes. |
| 206 | S20 Type costs | "Packaging you pay (£)" / "Shipping you pay (£)" | Minor | Fixed now | The labels follow A8.4's "Shipping and packaging you pay", on S20, its header and the S4 column pickers. |
| 207 | S20 Type costs | "...units sold in the last 30 days have a cost" | Major | Fixed now | The coverage line now asks `getCostCoverage` for the same 30 days the rows count, so both lines use one period. |
| 208 | S20 Type costs | " · current cost £{x}" | Major | Fixed now | `listSkuCosts` already serves the cost, so each row shows it. |
| 209 | S20 Type costs | "Nothing was saved, because no product cost was entered." | Major | Fixed now | Only the rows that saved are cleared, so a failed row keeps what was typed, and an empty save says why. |
| 210 | S20 Type costs | "This cost was not saved. Try again." | Minor | Fixed now | The fallback now gives a next step. |
| 211 | S20 Type costs | "Save costs" | Minor | Fixed now | The button says what it saves. |
| 212 | S20 empty | "Your products appear here once MyShopEdge has read your shop for the first time." | Minor | Fixed now | "Sync" is gone. |
| 213 | S5 Business details | "This step is optional. It lets MyShopEdge show your VAT and tax dates." | Minor | Fixed now | The fragments are sentences. |
| 214 | S5 Business details | "...so your progress towards the VAT registration threshold counts them." | Major | Fixed now | "The VAT line" is replaced by A8.4's term. `tax.py` adds other-channel sales to the VAT monitor, so the claim holds. |
| 215 | S5 Business details | "These figures help you plan. They are not tax advice." | Minor | Fixed now | The fragments are sentences. |
| 216 | S5 Business details | "Your business details could not be loaded." + "Nothing has changed. ..." | Major | Fixed now | A failed read now shows the error and no form, so blank answers can no longer overwrite the stored details. |
| 217 | S5 Business details | "Business details" / "Your business details were not saved. Try again." | Minor | Fixed now | The page title, heading and error now use the nav's name. |
| 218 | S5 Business details | "Are you VAT registered?" | Minor | Fixed now | The label is a question. |
| 219 | Export / data jobs | "...You can leave this screen and come back, and the file will be in the list below." | Major | Already fixed | `listExports` and `listAccountExports` now back the promise through the recent files list. |
| 220 | Export / data jobs | "MyShopEdge could not build the file. Your records are unchanged." | Minor | Already fixed | The failure says nothing was lost. |
| 221 | Export / data jobs | "You can build it again." | Minor | Already fixed | "At no cost" is gone. |
| 222 | Export form | "The file covers {formatDate} to {formatDate}..." | Minor | Already fixed | The dates are formatted. |
| 223 | Shell: nav | "Today overview" / "Money overview" / "Tax overview" | Minor | Already fixed | Each overview is named by its area. |
| 224 | Shell: nav | "Payouts and invoices" | Minor | Owner decision | The label waits on the owner's ruling between A8.4 and A29.7. |
| 225 | Shell: nav | "Records" | Minor | Kept | The nav label matches the heading of the Records screen, which is Area B's, and "records" is the plain accounting word that A8.2 prefers. |
| 226 | Shell: top bar | "Updated {stamp}, now out of date" | Major | Already fixed | The stale state is stated in words as well as colour. |
| 227 | Shell: top bar | alt "MyShopEdge home" | Minor | Already fixed | The link's purpose is in its text. |
| 228 | Six screens | `<section>` | Minor | Already fixed | No page under `app/(site)` renders a second `<main>`. |
| 229 | Reviewer | "Reviewer sign-in" | Minor | Already fixed | `reviewer/layout.jsx` gives the page its title. |

## Missing states, per screen

| Screen | Status | What was done, or why |
|---|---|---|
| S17 Start | Fixed now | A deliberate sign-out now reaches S37, and the unconfigured error already had a retry. |
| S37 Signed out | Fixed now | The signed-out state is reachable through `afterSignOut`. |
| S33 Billing | Fixed now | The retry and the past-due way forward were already there. The ended state now shows the plans. The card step still has no way back, which is kept, because the subscription exists at Stripe by then and the screen says the plan is fixed. |
| S34 Confirmed | Fixed now | The past-due loop was already fixed. A `redirect_status=processing` arrival now says the bank is still confirming the card and nothing has been charged. |
| S38 Payment failed | Needs building | A self-service card change exists since 8 October. When Stripe retries, and when the plan ends, still needs the service to read both from Stripe. |
| Account closing | Already fixed | The error state no longer claims the service was unreachable. |
| TikTok callback | Fixed now | The unsupported state has an action and now says no figures will appear. The first read starts at connection since 8 October. |
| S1 Connect | Kept | The audit judged the busy button label acceptable. |
| Your shops list | Fixed now | `/shops?all=1` reaches the list for a one-shop seller. |
| S2 First sync | Fixed now | The recovery actions and the waiting state were already fixed. A failed progress check now says so and keeps checking. |
| S35 Continue setting up | Fixed now | A failed subscription or tax request reads as not known. |
| S3 Costs choice | Kept | The audit found no state missing. |
| S4 Upload | Fixed now | Uploading and applying now each have a busy state, and the storage error is in plain words. |
| S20 Type costs | Fixed now | A partial failure keeps the failed rows, and existing costs are shown. A failed coverage read still hides the line, which the audit judged acceptable. |
| S5 Business details | Fixed now | A failed read shows an error and no form. |
| Export / data download | Already fixed | The recent files list lets a seller come back to a job, and the failure says nothing changed. |
| AppBar | Already fixed | The stale state is in words. A failed freshness read still leaves the stamp out by design. |

## Checks run after the changes

| Check | Last line |
|---|---|
| `npm run lint` (web) | `eslint src` printed no problem |
| `npm run check` (web) | `tsc -p jsconfig.json` printed no error |
| `npm run build` (web) | `ƒ  (Dynamic)  server-rendered on demand` |
| `ruff check .` | `All checks passed!` |
| `python3 tests/test_contract_conformance.py` | `every served route is in the contract` |
| `python3 tests/test_handlers_smoke.py` | `every handler executed and returned what it promised` |
