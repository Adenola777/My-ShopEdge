# The sign-in journey, landing page to Today, audited 28 September 2026

The owner asked for the journey from the landing page to the dashboard to be audited and
for what is broken to be fixed. It was walked in a browser against the local service and
the local copy of development, signed out and then signed in, and checked against the
onboarding order A14.2 rules:

```
S17 Start  ->  S1 Connect TikTok Shop  ->  S2 First sync  ->  S33 Plan and card  ->  ...  ->  S6 Today
```

## What could not be walked here

This session's network policy blocks the live site, the Render service, Stack Auth and
gov.uk, so three things were not exercised: the Stack sign-in and sign-up pages themselves,
the OAuth return from Google, GitHub or Microsoft, and the live deployment. A real sign-in
on 24 September proved the token path (CLAUDE.md). Signed-in screens here were reached
through the local proxy, which attaches a QA seller's token the way a Stack cookie would.

## Findings

| # | Found | Fixed |
|---|---|---|
| 1 | **Nothing linked to S33 Plan and card.** A seller could connect a shop and use every screen and was never offered a plan, so no trial could ever start | `lib/onboarding.js` sends a seller with no plan to `/billing` from `/shops` and from S2 |
| 2 | After TikTok returned the seller, the button led to `/shops` and so to Today, skipping S2 First sync | The button leads to the shop's S2 |
| 3 | S2's button led to Products, skipping S33 | It leads to the plan when there is none, and to Products after |
| 4 | `/billing` opened for a visitor who was not signed in, and told them "Your shop is connected" without checking | It sends a signed-out visitor to Start and a seller with no shop to connect one, and a seller whose trial is running is told so instead of being shown the plans |
| 5 | `/billing/confirmed` opened for a visitor who was not signed in | It sends them to Start |
| 6 | **`NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` is not set on Vercel** (read from the project's environment on 28 September). The card form cannot load, and the button would first have created the subscription at Stripe, leaving a trial with no card | With no key the form says card payments are not set up and starts nothing. **The owner must add the publishable key on Vercel** for payments to work |
| 7 | The payment form and the confirmation page used classes the stylesheet does not have (`primary`, `error`), so their buttons rendered as plain links | They use `btn btn--primary` and `form-error`. Six layout classes of the form (`card-step`, `plan-choice` and others) are still unstyled |
| 8 | A seller who returns part way through was always sent to Today | `/shops` resumes at the step reached: First sync while the shop is being read, the plan while there is none, Connection problem when the connection has lapsed, otherwise Today. A14's S35 screen is still not built |

## Checked after the fixes

Signed out, every shop screen, `/`, `/shops`, `/billing` and `/billing/confirmed` end at
Start. Signed in, four account states were set on the local copy and restored afterwards:

| State | `/` ends at | Onward action |
|---|---|---|
| Shop connected, no plan | `/billing` | Card form refuses honestly, because no Stripe key is set locally |
| Shop still being read, no plan | S2 First sync | "Continue to your plan" to `/billing` |
| Trial running | Today | `/billing` says the trial is running |
| Connection lapsed | Connection problem | Reconnect button |

## Noticed and not changed

The Vercel project also holds `TIKTOK_APP_KEY`, `TIKTOK_APP_SECRET`, `TIKTOK_SERVICE_ID` and
`TIKTOK_TOKEN_KEY`, which the front end never reads because the service holds them on
Render, and three variables with malformed names (`NEXTPUBLICSTACKPROJECTID`,
`NEXTPUBLICSTACKPUBLISHABLECLIENTKEY` twice) that nothing reads. None was changed. Secrets the
front end does not need are better removed from it, and that is the owner's call.

S17 still lacks the privacy notice and terms links A14 requires, because neither page exists.
