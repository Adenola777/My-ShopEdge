# Copy audit status, Area C, 9 October 2026

This file records what became of every Major and Minor finding in Area C of `audit/COPY_audit_8_october.md` ("Settings, data, account control and shared errors"). The owner approved fixing them on 9 October 2026. The ten Blocking rows are outside this file and were left alone.

Each row was checked against the code as it stood at commit `c4cee28`, by searching for the quoted text rather than trusting the audit's line numbers. Paths are relative to `web/src` unless they start with `service/` or `api/`.

## Counts

| Status | Rows |
|---|---|
| Already fixed | 40 |
| Fixed now | 12 |
| Kept | 5 |
| Owner decision | 1 |
| Needs building | 1 |
| Needs Area D | 0 |
| **Total** | **59** (19 Major, 40 Minor) |

## Facts that decided several rows

- **Validation errors are now sentences.** `service/app/main.py` registers `validation_handler` for `RequestValidationError`, and `service/app/problems.py` turns FastAPI's error list into one sentence with code `validation_failed`. A form that shows `detail` therefore no longer receives an array.
- **The developer texts are gone from the service.** `auth_unconfigured` now says "Signing in is not available just now. Nothing on your account has changed. Please try again later." (`service/app/auth.py`), and `storage_unconfigured` says "Files cannot be uploaded or downloaded just now. Nothing you saved has been lost. Please try again later." (`service/app/storage.py`).
- **A `needs_reconnect` shop is not read.** `run_shop` in `service/app/tiktok_sync.py` skips it ("skipped: needs_reconnect"). The state is set by TikTok's expiry warning (`tiktok_webhooks.py`), by a failed refresh after the access token lapsed (`tiktok_api.refresh_connection`), and by a sync that finds no connection.
- **`Shop.last_synced_at` is the last complete read.** `tiktok_sync.py` sets it only when every domain of a run is `completed` or `partial`. The contract serves it on `Shop`.
- **Deletion stops renewal only for a live plan.** `billing.set_renewal_for_deletion` returns `none` unless the status is in `LIVE` (`trialing`, `active`, `past_due`).
- **Only the month summary equals a screen.** The docstring of `service/app/exports.py` says `month_summary` is built from `money_view.calculate`, so its totals equal Money's. The ledger and transactions files are not described as equal to any screen.
- **The other-channel list has no channel.** `OtherChannelMonth` in `api/openapi.yaml` holds `month`, `amount` and `updated_at` only.

## Findings

| Screen | Current text (short) | Severity | Status | What was done, or why |
|---|---|---|---|---|
| Alert settings, page header | "These thresholds decide when a variant is marked low on stock, when MyShopEdge reminds you about a return…" | Major | Already fixed | The header no longer says "coming back", and each of the three settings it names is now read by the service (`alert_notices.py`, `tiktok_sync._absorb`). |
| Delete my account, page header | "Your account closes now. After thirty days MyShopEdge erases your name and email and deletes your files." | Major | Already fixed | The header now names what is erased instead of saying the account is erased. |
| Profile and plan, footnote | "Deleting closes your account at once. After thirty days MyShopEdge erases your name and email…" | Major | Already fixed | The footnote now names the name and email and says the seller can cancel. |
| Delete, TikTok Shop connection row | "Ends now. MyShopEdge stops reading your shops but does not ask TikTok to withdraw your approval." | Major | Already fixed | The row now says that TikTok is not told, which matches `account_deletion.py`. |
| Delete, plan row | "Stops renewing now, with no refund" | Minor | Fixed now | The page reads getSubscription and shows the row only for a trialing, active or past due plan, hides it otherwise, and words it as "If you have one" when the plan could not be read. |
| Delete, tokens row | "Your TikTok sign-in details" / "Erased after 30 days" | Minor | Already fixed | "Stored TikTok tokens" was replaced with plain words. |
| Delete, take your data | "MyShopEdge can build a copy of everything it holds about you…" | Major | Already fixed | The unbacked "ready in a few moments" was removed, in the audit's own words. |
| Delete, form button | "Delete my account" / "Deleting your account" | Minor | Owner decision | The label names the whole feature, which is "Delete my account" in the page title, the links and A30.1, and the "delete everything" wording is open with the owner. |
| Delete, success | "MyShopEdge does not email this record, so please save or print this page before you sign out." | Major | Already fixed | The line no longer asks the seller to keep a record without saying how. Sending an email stays an owner decision. |
| Delete, success, invoices | "…keeps your TikTok fee invoices until at least {date}, because VAT records must be kept for six years." | Minor | Already fixed | "At least" covers the case where the stored date falls before the true one. |
| Delete, form error | fallback "Your account was not closed. Please try again in a moment." | Minor | Already fixed | The fallback is in the audit's terms, and `account_suspended` now tells the seller whom to email. The form also goes through the new failure helper (see "Every client form"). |
| Closing page, keep account | "Your account is active again" / "The deletion is cancelled, and nothing will be erased." | Major | Already fixed | `CancelDeletion` now shows a confirmation and says how many shops must be connected again. |
| Closing page, cancel error | "MyShopEdge could not be reached, so the deletion still stands." | Minor | Kept | The audit found it clear and asked for no change, and the sentence is still true. |
| Disconnect, page | "…Nothing you already have is deleted. Disconnecting does not change your plan…" | Major | Already fixed | The page now says the plan is unchanged and links to Profile and plan. |
| Disconnect, what stays | "…MyShopEdge reads from where it stopped… does not ask TikTok to withdraw the approval you gave it." | Major | Already fixed | "Resumes against" is gone, and TikTok not being told is stated. |
| Disconnect, already disconnected | "This shop is already disconnected" | Minor | Already fixed | The page reads `connection_status` from listShops and offers to connect again instead. |
| Disconnect, success | "Your shop is disconnected… Disconnecting does not change your plan." | Minor | Already fixed | The plan line and the links "Back to settings" and "Reconnect this shop" are present. |
| Disconnect, error | fallback "The shop was not disconnected. Please try again in a moment." | Minor | Already fixed | The fallback was reworded, and the form now goes through the new failure helper, which adds a Sign in link on a 401. |
| Settings hub, footnote | "Disconnecting stops updates and keeps everything you already have. It does not change your plan." | Major | Already fixed | Billing is now mentioned. |
| Settings hub, tax profile | "Tax profile" linked to `setup/tax` | Major | Already fixed | The label links to the tax profile page. |
| Settings hub, low stock | "Low stock threshold" / "{n} days of cover" | Major | Already fixed | The A8 term "days of cover" is used, and "alert" is gone from the label. |
| Settings hub, header | "This page shows how this shop is connected to TikTok and how it is set up." | Minor | Already fixed | The header is a full sentence. |
| Settings hub, status | fallback `["Not known", "quiet"]` | Minor | Already fixed | A status the page does not know reads "Not known". |
| Settings hub, unavailable value | "This did not load. Reload the page to try again." | Minor | Already fixed | The line now gives a next step. |
| Profile and plan, header | "This page shows how you sign in and which plan this account is on." | Minor | Already fixed | The header is a full sentence. |
| Profile and plan, name note | "Your name and email come from the account you sign in with, such as Google, so you change them there." | Minor | Already fixed | The provider is named. |
| Shared fallback | "We show nothing rather than risk showing a wrong number." | Minor | Fixed now | Six pages already passed `NOTHING_CHANGED` and `identity_syncing` already has its own wording. Export and Connection problem, which show no figures, now pass it too. |
| Shared, unreachable | "MyShopEdge could not load {what}. Please try again in a moment." | Minor | Already fixed | The voice is "MyShopEdge" throughout. |
| Shared, 404 | "That shop is not on your account." | Minor | Kept | The audit asked for no change on shop pages, and `/me` has no path parameter that could answer 404 for a missing shop. |
| Every client form | `r.data?.detail` shown as the error | Major | Fixed now | A new `components/FormFailure.jsx` is used by Alert settings, Disconnect, Other-channel sales, Delete, Keep my account, Export and Download my data. It adds a Sign in link on a 401, and on an `internal_error` it says to reload to see whether the change was made, because an unhandled error can come after a write. The service details are now seller sentences (see above), so they are shown as they come. |
| Export and data, unreachable | "MyShopEdge could not be reached, so no file was started." | Minor | Already fixed | `NO_FILE_STARTED` is used by both forms. |
| Export and data, ready | "Kept until" / {expires_at}, with a fresh link fetched on each click | Major | Already fixed | `openFile` asks the single read for a new signed link when Download is pressed. |
| Export and data, ready footnote | "MyShopEdge keeps this file for seven days, and you can build it again whenever you need it." | Minor | Already fixed | "At no cost" is gone. |
| Export and data, failed | "MyShopEdge could not build the file. Your records are unchanged." | Major | Fixed now | It now adds "Please try again, and if it fails a second time, email info@inspirecraftglobal.com." That address is the one the service gives sellers in `account_suspended`. The stored `failure_reason` is not in the contract, so it is not shown. |
| Export and data, polling | "MyShopEdge could not check on your file just now…" with "Check again" | Major | Already fixed | A failed poll now says so and offers a retry. |
| Export and data, expired | "This file has expired. You can build it again." | Minor | Already fixed | "At no cost" is gone. |
| Download my data, header | "This file holds everything MyShopEdge keeps about your account." | Minor | Already fixed | The header is a full sentence. |
| Download my data, list | "Your plan and settings", "The history of what was read from TikTok" | Minor | Already fixed | Both suggested items are in the list. |
| Download my data, button | "Build my data file" / "Starting" | Minor | Already fixed | The button uses the suggested words. |
| Download my data, why | "…It holds no buyer names or addresses, because MyShopEdge never keeps them…" | Minor | Kept | The audit found it backed and asked for no change. |
| Export, header | "An Excel or CSV file whose totals equal the screen." | Minor | Fixed now | It now reads "This page builds an Excel or CSV file of your figures. A month summary has the same totals as the Money screen for the same period.", which is what `exports.py` says and no more. |
| Export, summary | "The file covers {date} to {date} on the {basis} basis…" | Minor | Already fixed | Both dates go through `formatDate`. The line now also says the totals equal the Money screen only for a month summary, for the reason in the row above. |
| Export, button | "Build the file" / "Starting" | Minor | Kept | The audit found it clear. |
| Connection problem, needs reconnect | "TikTok no longer accepts MyShopEdge's permission to read your shop…" | Major | Fixed now | It now reads "MyShopEdge needs your approval on TikTok again. Until you give it, new orders, returns and payments are not read, and your figures stop at the last successful read.", which holds for all three causes of the state. |
| Connection problem, last read | (no date) | Minor | Fixed now | Each state now says "MyShopEdge last finished a read of this shop on {date}." from `last_synced_at`, or that no read has finished yet. |
| Connection problem, disconnected | "…everything continues from where it stopped." | Minor | Fixed now | It adds "Your plan is not changed while the shop is disconnected.", because no disconnect path calls billing. |
| Other-channel sales, header | "Sales you make outside TikTok, so the VAT monitor sees your whole turnover." | Minor | Fixed now | It now reads "Enter the sales you make outside TikTok, so MyShopEdge compares your whole turnover with the VAT registration threshold.", in A8.4's term. |
| Other-channel sales, amount | "Total sales for the month, before any fees (£)" | Major | Already fixed | The label says the figure is gross. |
| Other-channel sales, save | "Saving the same channel and month again replaces the earlier total." | Major | Needs building | The helper text is already in place. Showing each channel, and correcting or removing an entry, needs `listOtherChannelSales` to return channels (`OtherChannelMonth` has none) and a delete operation, which are contract changes. |
| Other-channel sales, saved | "MyShopEdge saved {channel} for {month}." | Minor | Already fixed | The message names what was saved. |
| Other-channel sales, channel input | helper "For example Etsy, eBay or a market stall." | Minor | Already fixed | The example moved from a placeholder to helper text tied to the input. |
| Other-channel sales, empty | "Nothing entered yet. Add a month above." | Minor | Fixed now | It now reads "You have not entered any months yet. Add one above." |
| Other-channel sales, errors | "Choose the month." and two others | Minor | Kept | The audit found them clear and in house style. |
| Alert settings, saved | "Your thresholds are saved." | Minor | Already fixed | The message is a full sentence. |
| Alert settings, tolerance | "…is raised as a discrepancy for you to check." | Minor | Already fixed | The destination is named, and `tiktok_sync._absorb` does insert into `discrepancies`. |
| Alert settings, inputs | `aria-describedby` on each input | Minor | Already fixed | Each helper is tied to its input. The error is a form-level message rather than one input's, so no single input is marked invalid. |
| Alert settings, page name | "Alert settings" against the nav's "Alerts" | Minor | Fixed now | The nav label in `lib/nav.js` now reads "Alert settings". "Stock thresholds" no longer fits, because the page also sets the return check reminder. |
| Disconnect, browser title | `title: "Disconnect this shop"` | Minor | Already fixed | The title uses the suggested words. |
| Export, browser title | `title: "Export"` | Minor | Fixed now | The title now reads "Export your figures". |

## Missing states per screen

| Screen | State now |
|---|---|
| Settings hub (S15) | The tax profile row links to its page, and a value that fails reads "This did not load. Reload the page to try again." |
| Profile and plan (S41) | `email_unverified`, `email_required` and `account_suspended` each have their own wording in `ApiProblem.jsx`. A live plan can stop renewal and change its card (`PlanControls`). |
| Alert settings (S27) | A validation failure is a sentence, so the form shows it. The return check reminder is used by `alert_notices.py`. |
| Download my data (S31) | A failed poll says so and offers "Check again". A failed build says the records are unchanged and whom to email. Earlier files are listed, and Download fetches a fresh link. |
| Delete my account (S30) | The success card says no email is sent. The plan row now appears only when there is a live plan. Sending an email is an owner decision. |
| Closing page (A30.1) | A cancellation shows its confirmation before the seller moves on. |
| Disconnect (S29) | A shop already disconnected has its own state, and success links back to Settings and to reconnecting. |
| Connection problem (S28) | Each state now gives the last complete read. |
| Other-channel sales (S24) | Saving names what was saved. Seeing, correcting or removing one channel's entry needs building, as in the row above. |
| Export (S23) | The same as S31, and blank custom dates now return a sentence from the service. |

## Unbacked promises

| Promise | State now |
|---|---|
| Erasure "after thirty days" | Still depends on the cron job `My-ShopEdge-erase`, whose variables are the owner's to set on Render. This session cannot read Render. The service sentences about it are Blocking rows. |
| Ledger kept "for the period financial records must be kept" | The screen and the service now say that MyShopEdge has not yet set when the ledger is deleted. The period is an owner decision. |
| A confirmation email | The screen says no email is sent. Sending one is an owner decision, because nothing in the service sends email. |
| "Leave this screen and come back" | Backed since 8 October by `listExports` and `listAccountExports`, which the screen shows as recent files. |
| "Link works until {7 days}" | Replaced by "Kept until", with a fresh link on each click. |
| "Coming back window" | Replaced by "Return check reminder (days)", which `alert_notices.return_check_notices` reads. |
| "Low stock alert" | Backed since 9 October by `alert_notices.low_stock_notices`, which raises one notice per spell of low stock. |
| "Ready in a few moments" | Removed from the delete screen. |
| Disconnect "stops reading from TikTok" | Backed, as the audit found. |
| Plan "stops renewing now, with no refund" | Backed by `billing.set_renewal_for_deletion`, which has run against a stand-in Stripe client only. The row is now shown only when there is a plan to stop. |

## Files changed

- `web/src/components/FormFailure.jsx` (new)
- `web/src/components/SettingsForms.jsx` (the three forms' error handling only)
- `web/src/components/AccountDeletion.jsx` (the two forms' error handling only)
- `web/src/components/SetupForms.jsx` (the failed build line, the export summary line and the Export and Download my data error handling only; the shared `failure` helper used by Areas A and B is unchanged)
- `web/src/app/shops/[shopId]/settings/delete/page.jsx`
- `web/src/app/shops/[shopId]/connection-problem/page.jsx`
- `web/src/app/shops/[shopId]/other-sales/page.jsx`
- `web/src/app/shops/[shopId]/money/export/page.jsx`
- `web/src/lib/nav.js` (the Alert settings label only)

No service message, contract, schema or financial rule was changed. None of these screens has been driven in a browser since the change. The checks were lint, type check, build, ruff, the contract test and the handler smoke test.
