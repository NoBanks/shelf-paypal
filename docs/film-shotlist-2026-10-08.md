# SHELF x PayPal demo film: shot list (target 2:40, hard cap 2:59)

Format: caption-driven music cut, no voiceover. One NoBanks Nearby track (Ryan picks). 24 fps, 1920x1080.
Rules from Devpost: under 3 minutes, YouTube public or unlisted, no third-party music or trademarks
(PayPal's own button is fine, they are the sponsor). Judges only watch the first 3 minutes.

Raw footage: evidence/footage/<date>/*.webm (Playwright recordings of the live site at 1280x800),
evidence/gallery/*.png (3:2 stills), Ryan's phone b-roll (optional).

| Time | Shot | Caption |
|---|---|---|
| 0:00-0:08 | B-roll or still: a shelf of real stuff (Ryan's prints, a lamp, a jacket). If no b-roll, slow push on the storefront grid. | "Everyone owns a shelf of money." |
| 0:08-0:16 | Title card on the mint/dark brand. | "SHELF x PayPal. Photos in, PayPal money out." |
| 0:16-0:35 | Dashboard: photos dragged in, card appears "processing", live crew feed scrolls (curator, appraiser, copywriter lines). | "CURATOR sees it and discloses every flaw." / "APPRAISER prices it from cited comps, or abstains." / "COPYWRITER writes it honest." |
| 0:35-0:45 | Draft card, one click Approve, status flips LIVE. Cut to storefront with the item. | "A human approves. Agents never publish alone." |
| 0:45-1:20 | THE SALE (film's heart). Item page with Pay with PayPal and Pay Later buttons. Click. PayPal window: sandbox buyer logs in, review screen, Pay. Window closes, item page shows "Paid. PayPal capture 6K1...". | "Buyer pays with PayPal." / "Orders v2: create, approve, capture." / "The sale books itself." |
| 1:20-1:40 | Ledger: paid entry with PayPal capture id, net after fees. Dashboard card: PAID $45.00 (net $42.94), capture id, buyer email. | "Every dollar lands in a ledger, keyed by the PayPal capture id." |
| 1:40-2:00 | Dashboard: tracking number typed, Ship it. Card flips SHIPPED. PayPal order page (developer dashboard or API JSON) shows tracker SHIPPED. | "SHOPKEEPER posts tracking to PayPal. Buyer is notified." |
| 2:00-2:15 | Shopkeeper note appears on the card. Terminal or UI: bookkeeper report text ("Ledger and PayPal records match completely"). | "BOOKKEEPER reconciles the ledger against PayPal, not the other way round." |
| 2:15-2:30 | Quick cut: architecture line (ADK crew -> Orders v2 -> webhook -> ledger), pytest "57 passed", Render dashboard live, webhook registered. | "Google ADK + Gemini. PayPal Orders v2, JS SDK v6, webhooks. 57 offline tests. Live on Render." |
| 2:30-2:40 | Close on the storefront. URL card. | "SHELF x PayPal. shelf-paypal.onrender.com" / "an agent crew by NoBanks Nearby" |

Captions: plain sans, no em dashes, no hype words. Every claim on screen is something the footage shows.

## Assets checklist
- [ ] Track pick (Ryan). Needs a clean drop around 0:45 for the sale.
- [x] Live-site footage (automated recordings; re-record once real item photos are in).
- [ ] Upload + crew feed footage with REAL photos (needs 2 to 3 phone photos of one real item from Ryan).
- [x] Stills: storefront, item page, dashboard, ledger (evidence/gallery).
- [ ] B-roll (optional): shelf of items, packing a mailer, USPS handoff.
- [ ] Terminal captures: pytest run, Render deploy, webhook list.
- [ ] Cut, captions, export 1080p, upload to YouTube (unlisted), paste link into Devpost project details.
