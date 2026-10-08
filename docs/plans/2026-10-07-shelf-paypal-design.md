# SHELF x PayPal: design (2026-10-07)

Target: PayPal AI Hackathon 2026 (Devpost). Primary prize: Best Use of Agentic Commerce.
Deadline Nov 12, 2026 noon Pacific. Internal submit Nov 10. Ryan offline Oct 16 to 23.

Decisions below were made by Claude while Ryan was offline, using the recommendations
Claude would have given. Ryan can overrule any of them on Oct 11.

## One-liner
Photograph an item. An agent crew identifies it, prices it from cited comps, writes an
honest listing, and (after one human tap) lists it on a storefront with a real PayPal
checkout. When a buyer pays, agents capture the PayPal order, post tracking, and book
the sale in a ledger keyed by the PayPal capture ID. Photos in, PayPal money out.

## What is reused vs new
Reused from SHELF (Aug 2026, github.com/NoBanks/shelf-agentic): the ADK crew pattern
(curator, appraiser, copywriter), free keyless comps search, the local/Firestore store,
the FastAPI app with live SSE agent feed, the mint/forest UI. Copied in as a starting
point and modified, with attribution in README.
New in this window: everything PayPal, two new agents (shopkeeper, bookkeeper), the
checkout UI, order and ledger model changes, tests, deployment, video.

## Approaches considered
1. PayPal Agent Toolkit (Python) with LangChain or CrewAI. Rejected: would mean
   rewriting the crew off Google ADK; toolkit has no ADK adapter.
2. PayPal MCP server (@paypal/mcp) consumed by ADK's MCPToolset. Good story for
   judges ("agents use PayPal's own MCP tools"). Needs Node at runtime plus an access
   token. Kept as the shopkeeper's tool source, with a REST fallback.
3. Direct Orders v2 REST through a small typed client (httpx). Simplest, fully
   testable offline with a fake server, no Node dependency on the hot path.
Chosen: 3 for the checkout path (storefront button -> create order -> capture) because
it must never flake in the demo, plus 2 for the agent layer so the shopkeeper and
bookkeeper genuinely use PayPal's agent tooling. If MCP proves fragile, the same agent
tools call the REST client; the agent code does not change.

## Architecture
```
phone photos -> POST /api/items -> ADK item_crew (curator -> appraiser -> copywriter)
   -> draft -> human approves -> status live -> storefront /store
buyer clicks PayPal button (JS SDK v6) -> POST /api/paypal/orders {item_id}
   -> PayPalClient.create_order (Orders v2, intent CAPTURE, custom_id=item_id)
buyer approves in PayPal popup -> POST /api/paypal/orders/{id}/capture
   -> PayPalClient.capture_order -> status COMPLETED, capture id
   -> item status sold, ledger entry {kind: paid, paypal_capture_id, amount}
   -> shopkeeper agent runs post-sale: confirm order (get_order), add tracking
      (POST /track) when seller enters a tracking number, write buyer note
bookkeeper agent: summarizes the ledger and reconciles against PayPal transactions
webhook POST /api/paypal/webhook (PAYMENT.CAPTURE.COMPLETED) as a second source of
   truth so a closed popup never loses a sale
```

## Components (Python 3.11)
- `shelf/agents.py`: curator, appraiser, copywriter (reused), shopkeeper, bookkeeper
  (new) as ADK LlmAgents. Shopkeeper tools: get_order, add_tracking, book_sale.
- `shelf/paypal.py`: PayPalClient (token cache, create_order, get_order,
  capture_order, add_tracking, verify_webhook). Pure httpx, sandbox base URL by env.
- `shelf/checkout.py`: deterministic glue: item -> order payload, capture result ->
  item/ledger transitions. No LLM in the money path, by design (the model is not
  trusted with the cash rule; same law as the listing engine).
- `shelf/store.py`: Item gains paypal_order_id, paypal_capture_id, buyer_email,
  tracking_number, carrier. LedgerEntry gains paypal_capture_id.
- `shelf/webapp.py`: existing routes plus /api/paypal/config, /api/paypal/orders,
  /api/paypal/orders/{id}/capture, /api/paypal/webhook, /api/items/{id}/ship.
- `shelf/ui.py`: storefront gets an item page with the PayPal v6 button; dashboard
  shows sold items with capture id and a "ship it" box; ledger shows PayPal ids.
- `tests/`: fake PayPal server (respx) for create/capture/track; checkout state
  machine; webhook verify; parser units carried over.

## Error handling
- Capture failure or DECLINED: item stays live, ledger untouched, buyer sees a plain
  message. Logged with the PayPal debug id.
- Webhook and capture both idempotent on capture id: second arrival is a no-op.
- Token expiry: client refreshes on 401 once.
- Gemini quota: existing key-rotation retry loop; pool now also reads
  GEMINI_API_KEY_N env vars present on this PC.

## Hosting
Render free web service (sponsor prize eligibility). JSON store on ephemeral disk plus
a seed script so a redeploy never shows an empty store. Firestore stays optional.

## Out of scope (YAGNI)
Buyer agent that shops autonomously (ask Ryan Oct 11), Store Sync / Agent Ready
(gated), payouts, subscriptions, multi-currency, auth for the seller dashboard
(single-seller demo; a SHELF_ADMIN_TOKEN env guards approve/ship if set).

## Testing
pytest offline suite (no network, no keys). One live smoke script against the
sandbox once credentials exist: create, (manual approve), capture, track.
