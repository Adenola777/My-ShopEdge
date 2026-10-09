# Copy audit of 8 October 2026, Area D, service rows: status on 9 October 2026

This file records where each Major and Minor row of Area D stands that names a file under `service/`. It covers rows 1 to 80 of the findings table in `audit/COPY_audit_8_october.md`. The Blocking rows 3, 4, 5, 18 and 23 are left alone, as the brief directs, and the landing page rows 81 to 97 are handled separately. Each current text below was read from the file on 9 October 2026, after copy batches 1 to 3, and line numbers are not given because they move.

## Counts

| Status | Rows |
|---|---|
| Already fixed | 63 |
| Fixed now | 7 |
| Kept | 2 |
| Owner decision | 1 |
| Needs building | 2 |
| **Total** | **75** (Major 28, Minor 47) |

## Rows

| # | Current text (short) | Severity | Status | What was done, or why |
|---|---|---|---|---|
| 1 | `problems.py` `TITLES`, for example 422 "Some details need checking." | Major | Already fixed | The title now comes from the HTTP status as a sentence, and the machine code stays in `code` and `type`. |
| 2 | `validation_handler`: "Threshold must be 0 or more." | Major | Already fixed | `main.py` registers a `RequestValidationError` handler that answers in the problem shape with one sentence per failing field. |
| 6 | "One TikTok Shop connection" (Starter) | Major | Owner decision | The wording of this line on Starter is one of the owner's open decisions, so it was not changed. |
| 7 | "Product costs, uploaded or typed"; "Exports on a sales basis or a cash basis" | Major | Kept | The service serves uploads and exports in code, and whether production has the R2 variables cannot be read from this session, so the line was not narrowed. |
| 8 | "Gross profit after returns, by product" | Minor | Already fixed | The Growth line uses A8.2's figure name. |
| 9 | Starter lists "Up to 100 orders a month" | Minor | Already fixed | Starter states its allowance like the other plans, and the order count exists since 9 October (A16.3). |
| 10 | "Sales, fees and payouts, reconciled to every statement" | Minor | Kept | The audit asked for no wording change, and real statements on production now carry fees and all 107 reconcile (CLAUDE.md, fault 13), so the claim is no longer unverified. |
| 11 | "Starter covers a shop taking up to 100 orders a month." | Minor | Already fixed | The three straplines state each plan's order allowance as full sentences. |
| 12 | Evidence label "Net proceeds less cost of goods sold" | Major | Already fixed | "Contribution" is gone. The label names its arithmetic rather than "Gross profit", because the figure leaves out shipping and packaging you pay and so is not A8.5's gross profit. |
| 13 | "Its net proceeds were less than the cost of the units sold and kept. You can check..." | Major | Already fixed | "TikTok's cut" and the "Options:" fragment are gone. |
| 14 | "{name} lost £X on N units sold so far this month." | Minor | Already fixed | The period is named as the month so far. "gross loss" was not used, for the reason given in row 12. |
| 15 | "Shipping and packaging you pay took {p}p of every £1 of net sales for {name}." | Major | Already fixed | The A8.4 term is used and the base is named as net sales. |
| 16 | Labels "Net sales", "Shipping and packaging you pay, from your cost figures" | Minor | Already fixed | Both labels use the A8.4 terms. |
| 17 | Label "Cost of goods sold, less returned units" | Minor | Already fixed | The audit's suggested label is in place. |
| 19 | "Not known, because not every product sold in the period has a cost price." | Major | Already fixed | `KEPT_REASONS` maps both codes to sentences, so no code reaches the file. |
| 20 | Confidence "Estimated, because TikTok has not yet settled some amounts in the period." | Minor | Already fixed | `CONFIDENCE_WORDS` maps each confidence code to words. |
| 21 | "We could not prepare this download because of a fault at our end. Your records are unaffected..." | Major | Already fixed | Both failure reasons use the audit's suggested text. |
| 22 | "Files cannot be uploaded or downloaded just now. Nothing you saved has been lost. Please try again later." | Major | Already fixed | The jargon is gone and the message says what happened to the seller's data and what to do. |
| 24 | "Gross profit after returns so far this tax year, by sale date, ..." | Minor | Already fixed | The basis line uses A8.2's figure name. |
| 25 | "MyShopEdge does not have this tax year's Income Tax and National Insurance rates..." | Minor | Already fixed | "loaded" is gone. |
| 26 | "TikTok's count for {title} rose by N units." / "...Stock on hand is ..." | Major | Already fixed | "On the shelf" and "taken ours off" are gone, and the body says what MyShopEdge removed and why. |
| 27 | "Your TikTok Shop connection is close to expiring." | Minor | Needs building | A date needs a verified source, and TikTok's webhook payload fields are unverified and whether `refresh_expires_at` is the authorisation expiry is unknown (CLAUDE.md, blocked table). |
| 28 | Deauthorisation writes no notification | Minor | Needs building | The webhook handler would need to insert a notification on `deauthorization`, which is a change of behaviour rather than wording. |
| 29 | "TikTok's stock count rose by {r}. That is more than the {t} units..." | Minor | Already fixed | "absorbed" is gone from the seller's text. |
| 30 | "TikTok's count rose from {b} to {a}, so your adjustment was reduced from {x} to {y}." | Minor | Already fixed | The reason is one sentence in one tense. |
| 31 | "TikTok would not renew MyShopEdge's access to your shop. Reconnect the shop..." | Major | Already fixed | No raw TikTok code is shown. |
| 32 | "TikTok has not given MyShopEdge all the access it needs. Reconnect the shop..." | Major | Already fixed | No scope identifier is shown. |
| 33 | "part of the last update from TikTok failed, so some figures may be missing" | Major | Already fixed | The label says that figures may be missing. The audit's "We will try again at the next update" was not added, because `tiktok_sync.window` starts the next run from the shop's latest completed or partial domain, so a failed range is not certain to be read again. |
| 34 | "An update stopped because your shop needs reconnecting to TikTok" | Minor | Already fixed | The shop is named as what needs reconnecting, and "sync" is gone. |
| 35 | "Your TikTok Shop connection expires in {n} days" | Minor | Already fixed | The connection is named the same way as elsewhere. |
| 36 | "Your figures may be out of date. MyShopEdge last brought them up to date {h} hours ago." | Minor | Already fixed | Both sentences carry a subject and a verb. |
| 37 | "{n} fee this month has a name MyShopEdge does not recognise" | Minor | Already fixed | The audit's suggested wording is in place. |
| 38 | "{n} return is waiting to be checked" | Minor | Already fixed | The fragment is now a clause. |
| 39 | `returns.py`: "This variant had no cost when it sold, ..." | Minor | Fixed now | The refusal now reads "had no cost price on the day it sold" and "Add its cost price", which matches the products and Today wording. |
| 40 | "{Stripe's text}. Nothing was charged and the trial has not started. Try another card, ..." | Major | Already fixed | The outcome and the next step are always appended. |
| 41 | "Plans cannot be started or changed just now. Nobody has been charged. ..." | Major | Fixed now | The jargon was already gone. "Nobody has been charged. Please try again later." now reads "You have not been charged. Try again later.", as row 42 asked for the neighbouring message. |
| 42 | "This plan cannot be started at the moment. You have not been charged. ..." | Minor | Already fixed | The audit's suggested text is in place. |
| 43 | `stripe_error`: "...so nothing was changed. Please try again in a moment." | Minor | Fixed now | Each `stripe_error` keeps the outcome that fits its operation, and all five now end with the same next step, "Try again in a few minutes." |
| 44 | "Connecting a TikTok shop is not available just now. Nothing has changed..." | Major | Already fixed | Both unconfigured codes carry one wording with no jargon. |
| 45 | "TikTok did not accept the connection, so your shop is not connected. Start the connection again..." | Major | Already fixed | The next step is given. |
| 46 | "TikTok turned down our request, so your shop is not connected. ..." | Major | Already fixed | TikTok's own message is no longer shown. |
| 47 | "That TikTok account does not run a TikTok Shop. Sign in to TikTok with the account..." | Major | Already fixed | The audit's suggested text is in place. |
| 48 | "TikTok did not give MyShopEdge access to a shop on that account. ..." | Major | Already fixed | The audit's suggested text is in place. |
| 49 | "That shop is already connected to a different MyShopEdge account, so it was not added here..." | Major | Already fixed | The message gives a route forward. |
| 50 | "TikTok did not answer, so your shop is not connected. Start the connection again in a few minutes." | Minor | Already fixed | Both `tiktok_unreachable` sites carry one wording. |
| 51 | "Something went wrong starting the connection. Go back to MyShopEdge and start it again." | Minor | Already fixed | The developer text is gone. |
| 52 | "Signing in is not available just now. Nothing on your account has changed. ..." | Major | Already fixed | No environment variable is named. |
| 53 | "That email address already belongs to an account that signs in another way. Sign in that way instead." | Major | Already fixed | The promise of linking is gone. |
| 54 | "Your sign-in gave us no verified email address, so we cannot set up your account. ..." | Major | Already fixed | The next step is given. |
| 55 | "This account is suspended, so it cannot be used. Email info@inspirecraftglobal.com..." | Major | Already fixed | Both sites carry the audit's suggested text. |
| 56 | `account_deletion.py`: "Until {day} you can cancel the deletion by signing in again." | Minor | Fixed now | The deletion summary now says that signing in again takes the seller to the account closing page, which matches `auth.py` and the redirect in `web/src/components/ApiProblem.jsx`. |
| 57 | "We could not confirm your sign-in. Sign in again." | Minor | Already fixed | The reason is given. |
| 58 | `auth.py`: "Your sign-in provider has not verified this email address yet." | Minor | Fixed now | "sign-in provider" now reads "The service you signed in with". Google is not named, because the reviewer path signs in by email and password. |
| 59 | "We could not find your account. Sign in again." | Minor | Already fixed | Both sites give the reason. |
| 60 | "This account is not being deleted, so there is nothing to cancel." | Minor | Already fixed | The audit's suggested text is in place. |
| 61 | `main.py`, `problems.py`: "Something went wrong at our end." | Major | Fixed now | Both 500 answers now share `INTERNAL_ERROR`, which tells the seller to refresh to see whether the change was saved and gives the support address. The 500 title is unchanged. |
| 62 | "That page or action does not exist in MyShopEdge." | Minor | Already fixed | Starlette's 404 and 405 text is replaced. |
| 63 | "Something went wrong sending this change, so nothing was saved. Refresh the page and try again." | Minor | Already fixed | Both idempotency refusals use `RESEND`. |
| 64 | "That list could not be loaded. Refresh the page." | Minor | Already fixed | All three cursor refusals carry it. |
| 65 | "These costs are already applied. Upload the file again to change them." | Minor | Already fixed | Both sites carry the wording with the next step. |
| 66 | "The file has not finished uploading. Upload it again, then continue." | Minor | Already fixed | Both sites carry the audit's suggested text. |
| 67 | "{n} of the rows you chose could not be matched to a product, so no costs ..." | Minor | Already fixed | The audit's suggested text is in place. |
| 68 | "The {name} is in {x} and this shop sells in {y}. Enter it in {y}." | Minor | Already fixed | The currency refusals share one form with a next step. The invoice refusal names the statement's currency, because an invoice is checked against its statement. |
| 69 | "MyShopEdge could not read the text in this CSV file. Save it again as CSV UTF-8..." | Minor | Already fixed | All three file refusals give a next step. |
| 70 | `cost_files.py`: `The amount in the "{column}" column "abc" is not an amount, ...` | Major | Fixed now | The column was already named, but the sentence did not parse. `read_amount`'s reasons now read `is "abc", which is not an amount`, so the row reason is a sentence. |
| 71 | "The period ends before it starts. Choose an end date on or after the start date." | Minor | Already fixed | All four sites carry one wording with a next step. |
| 72 | "...because only {n} unit is/units are on hand." | Minor | Already fixed | The verb agrees with the number. |
| 73 | "The channel name can be up to 100 characters." / "The invoice number can be up to 64 characters." | Minor | Already fixed | Both state the limit. |
| 74 | "A notification marked {done} cannot be marked {read} again." | Minor | Already fixed | The status words are the ones the seller sees. |
| 75 | "TikTok holds more unsettled transactions than MyShopEdge can total here, ... Your figures in Money are unaffected." | Minor | Already fixed | The internal wording is gone and the effect is stated. |
| 76 | "TikTok did not answer just now, so no expected payouts are shown. Try again in a few minutes." | Minor | Already fixed | The next step is appended. |
| 77 | "This variant is not on the original order, so the return cannot be recorded against it." | Minor | Already fixed | The audit's suggested text is in place. |
| 78 | "MyShopEdge does not have the current VAT registration threshold yet, ..." | Minor | Already fixed | "configured" is gone. |
| 79 | "Enter the date you registered for VAT as a full date." | Minor | Already fixed | The audit's suggested text is in place. |
| 80 | "Every connected shop is disconnected now, and MyShopEdge stops using its TikTok sign-in details." | Minor | Already fixed | "tokens marked revoked" is gone. |

## Checks

`ruff check .` at the repository root passed. These service tests passed: `test_auth_verification`, `test_contract_conformance`, `test_handlers_smoke`, `test_business_date`, `test_cost_files`, `test_set_aside`, `test_insights_trends`, `test_tiktok_client`, `test_data_api_guard` and `test_webhook_tiktok`. No test asserted on a string that changed. No string that changed is matched by text in `web/src`.
