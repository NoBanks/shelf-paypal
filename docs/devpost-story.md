# Devpost story (as submitted draft, 2026-10-08)

## Inspiration
Everyone owns a shelf of stuff worth money that never gets sold, because selling is work: identify the thing, research a fair price, write a listing that does not oversell, take the payment, ship it, keep the books. I have funded my own life this way, one item at a time. SHELF started as a bet that a small crew of agents can do the boring 90 percent, and a human should only do the two things that matter: approve the listing, and hand the box to the mail carrier. For this hackathon the bet got bigger: let the agents close the sale too, through PayPal.

## What it does
Photograph an item and upload it. A CURATOR agent (Gemini vision) identifies it and discloses every flaw it can see. An APPRAISER prices it from cited comparable listings, or abstains rather than invent a number. A COPYWRITER writes a plain, honest listing. You approve it with one tap and it is live on a storefront with a real PayPal checkout (JavaScript SDK v6, Pay with PayPal and Pay Later).

When a buyer pays, the Orders v2 capture is booked in a ledger keyed by the PayPal capture id, with net after fees and the buyer email. The SHOPKEEPER agent confirms the order with PayPal, books it, writes the buyer note, and when you type a tracking number it posts the tracker to PayPal so the buyer gets notified. The BOOKKEEPER agent reconciles the ledger against what PayPal says was captured and reports in plain text. Photos in, PayPal money out.

## How we built it
- Google ADK agent crew with Gemini: curator, appraiser, copywriter, shopkeeper, bookkeeper. The two new agents work only through typed tools over the deterministic money path.
- PayPal Orders v2 REST in the sandbox: OAuth client credentials, create order with intent CAPTURE and an experience context, capture, add shipment tracking, webhook signature verification. Idempotency keys on every write.
- PayPal JavaScript SDK v6 on the item page: createInstance, findEligibleMethods, createPayPalOneTimePaymentSession, Pay Later when eligible.
- Webhooks: PAYMENT.CAPTURE.COMPLETED is registered and signature-verified as a second source of truth, so a buyer closing the popup after approving never loses a sale. Booking is idempotent on the capture id.
- FastAPI web app with a live server-sent-events agent feed, a public storefront, a seller dashboard and a ledger. Deployed on Render (free tier) with a seeded demo store.
- 57 offline tests: the PayPal client against a fake sandbox, the checkout state machine, every HTTP route, the agent tools, the key pool.

## Challenges we ran into
- The v6 SDK docs page did not show the full button code; PayPal's sample repository on GitHub did, and the one gotcha is real: do not await createOrder() before start(), or the user activation is lost.
- The PayPal checkout opens as a separate window that automation only sees a few seconds later. Patience fixed it; so did reading the review screen's Pay button id (one-time-cta).
- Trust boundaries. The model never sets an amount. Every PayPal call reads the price from the approved item record or from PayPal itself. Writing that rule down early kept the agents simple.
- Sandbox buyer passwords live behind a masked field in the Developer Dashboard. We wrote it down the first time.

## Accomplishments that we're proud of
- A complete, real sale in the sandbox on the first live run: order, buyer approval, capture, ledger entry with the capture id, tracking posted, PayPal shows the tracker as SHIPPED.
- The shopkeeper wrote the buyer note in ten seconds and the bookkeeper reported "ledger and PayPal records match completely" three seconds later, both from live PayPal data.
- Honesty by design survived the money: flaws are still disclosed on the item page, right above the PayPal button.
- Solo build, nights and mornings around a full-time retail job.

## What we learned
Agents are at their best when each has one narrow job and the dangerous part is deterministic code they can only call through tools. PayPal's Orders v2 is small enough to learn in an evening if you read the OpenAPI schema instead of guessing. And a webhook as a second source of truth is cheap insurance for the one moment a popup closes early.

## What's next for SHELF
- Real inventory: the author's own prints and secondhand finds, listed and sold through the live store.
- PayPal MCP server tools for the shopkeeper so the agent can use PayPal's own agent tooling end to end.
- Payouts to a second seller, so a shared shelf (a family, a yard sale, a thrift shop) can split money automatically.
- A photo-quality coach agent and intake by video sweep: point the camera at the whole shelf.

## Prior work and disclosure
This extends SHELF (github.com/NoBanks/shelf-agentic, Google ADK, built by the same author in August 2026 for a Google hackathon). SHELF had the three listing agents, the dashboard with the live feed, a storefront page and a manual mark-sold ledger, and no payments at all. Everything PayPal, the shopkeeper and bookkeeper agents and their tools, the checkout state machine, the item page, the tests, the Render deployment and the video are new work in this hackathon window. Built with AI coding assistants, as the rules allow. MIT licensed.
