# SHELF x PayPal

**Photos in, PayPal money out.**

Photograph something you want to sell. An agent crew identifies it, discloses every
flaw it can see, prices it from cited comparable listings, and writes an honest
listing. You approve it with one tap. It goes live on a storefront with a real PayPal
checkout. When a buyer pays, the agents capture the PayPal order, book the sale in a
ledger keyed by the PayPal capture id, and post shipment tracking so PayPal notifies
the buyer. No human writes a listing, takes a payment, or does the books.

Built for the PayPal AI Hackathon 2026 (Devpost). MIT licensed.

## The crew (Google ADK + Gemini)

| Agent | Job | Tools |
|---|---|---|
| CURATOR | Sees the photos. Names the item, condition, every visible flaw. Never names a real brand it cannot read. | Gemini vision |
| APPRAISER | Prices from comparable listings, cites each one, or abstains. Never invents a number. | `comps_search` (free, keyless web search) |
| COPYWRITER | Writes the plain, honest listing. Every flaw the curator found is in the text. | Gemini |
| SHOPKEEPER | Closes the sale after PayPal captures: confirms the order with PayPal, books it, posts tracking, writes the buyer note. | `get_paypal_order`, `book_sale`, `add_tracking` (PayPal Orders v2) |
| BOOKKEEPER | Reconciles the ledger against what PayPal says was captured. Reports plainly. | `ledger_summary`, `list_paypal_captures` |

A human approves every listing before it goes live. The model never sets an amount:
every PayPal call reads the price from the approved item record or from PayPal itself.

## PayPal integration (sandbox)

- **Orders v2 REST** (`shelf/paypal.py`): OAuth client credentials, create order with
  `intent: CAPTURE` and `payment_source.paypal.experience_context`, capture, add
  shipment tracking, webhook signature verification. Idempotency keys on every write.
- **JavaScript SDK v6** on the item page (`<paypal-button>`,
  `createPayPalOneTimePaymentSession`, Pay Later button when eligible).
- **Webhooks**: `PAYMENT.CAPTURE.COMPLETED` is a second source of truth, so a buyer
  closing the popup after approving never loses a sale. Booking is idempotent on the
  capture id.
- **Agent tools**: the shopkeeper and bookkeeper call PayPal through typed tools, so
  the agents can only do what the deterministic money path already allows.

```
photos -> POST /api/items -> curator -> appraiser -> copywriter -> draft
seller taps Approve -> live on /store
buyer clicks PayPal -> POST /api/paypal/orders -> PayPal popup -> approve
-> POST /api/paypal/orders/{id}/capture -> paid, ledger entry with capture id
-> SHOPKEEPER confirms with PayPal, writes buyer note
seller enters tracking -> POST /api/items/{id}/ship -> PayPal tracker -> shipped
BOOKKEEPER: ledger vs PayPal captures, on demand
```

## Run it locally

Requirements: Python 3.11, a PayPal sandbox app (Client ID + Secret from the
[Developer Dashboard](https://developer.paypal.com/dashboard/)), a Gemini API key.

```bash
git clone https://github.com/NoBanks/shelf-paypal
cd shelf-paypal
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                 # fill in PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, GOOGLE_API_KEY
python -m scripts.seed_demo                          # three live demo items so the store is not empty
uvicorn shelf.webapp:app --port 8080 --env-file .env
```

Open http://127.0.0.1:8080 (seller dashboard), http://127.0.0.1:8080/store (storefront),
http://127.0.0.1:8080/ledger (ledger). Upload one to six photos of a real item on the
dashboard, watch the crew feed, approve the draft, then buy it on the store with a
sandbox buyer account (Developer Dashboard > Sandbox > Accounts).

Webhooks locally: expose port 8080 (for example `ngrok http 8080`), add a webhook in the
Developer Dashboard for `PAYMENT.CAPTURE.COMPLETED` pointing at
`https://<your-tunnel>/api/paypal/webhook`, and set `PAYPAL_WEBHOOK_ID`.

## Tests

```bash
pytest -q
```

The suite runs offline with no keys: the PayPal client against a fake sandbox
(`respx`), the checkout state machine against a PayPal double, every HTTP route, the
agent tools, the key pool, and the SHELF parser and store units carried over.

## Deploy

`render.yaml` deploys a free Render web service (the build seeds the demo store).
Set `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PUBLIC_URL`, `GEMINI_KEYS` and
`SHELF_ADMIN_TOKEN` in the Render dashboard. A `Dockerfile` is included for Cloud Run
or anywhere else.

## Honesty by design

- Flaws the curator finds are disclosed in the listing and on the item page, always.
- The appraiser cites comparable-price sources or abstains. It never invents.
- A human approves every listing before it goes live.
- No LLM touches an amount. The money path is deterministic Python with tests.
- The ledger stores the PayPal capture id for every sale, and the bookkeeper agent
  checks the ledger against PayPal, not the other way round.

## Prior work disclosure

This project extends [SHELF](https://github.com/NoBanks/shelf-agentic) (Google ADK,
built by the same author in August 2026 for a Google hackathon). SHELF had the
curator, appraiser and copywriter crew, the dashboard with the live agent feed, a
storefront page and a manual mark-sold ledger. It had no payments at all.

New in the PayPal AI Hackathon window (October 2026): the entire PayPal integration
(Orders v2 client, checkout state machine, capture, tracking, webhooks, JS SDK v6
item page), the SHOPKEEPER and BOOKKEEPER agents and their PayPal tools, PayPal
fields on the item and ledger models, the seller admin token, the demo seed, the
Render deployment, this README and the demo video. Written with AI coding
assistants, as the rules allow.

## License

MIT. See LICENSE.
