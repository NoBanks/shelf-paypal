# Live sandbox run, 2026-10-07 (first end-to-end sale)

Environment: PayPal sandbox, app "SHELF", seller sb-cnvay53257428@business.example.com,
buyer sb-4ieav53252700@personal.example.com. App running locally on port 8899.

| Step | Result |
|---|---|
| OAuth token | issued (client credentials) |
| POST /v2/checkout/orders | order 84X25444YP1514635, PAYER_ACTION_REQUIRED, intent CAPTURE, $45.00 |
| Item page, JS SDK v6 | "Pay with PayPal" and "Pay Later" rendered, checkout window opened |
| Buyer login + Pay | sandbox buyer, "Pay" clicked on the review screen |
| POST .../capture | COMPLETED, capture 6K145626FL1362222, gross 45.00, net 42.94 |
| Ledger | kind=paid, amount 45.00, paypal_capture_id 6K145626FL1362222, buyer email stored |
| POST /api/items/it_demo_print/ship | PayPal tracker accepted, USPS 9400111899223197428490, item shipped |
| Ledger | kind=shipped added; totals paid 45.00, net 42.94, shipped 1 |

Screenshots: ../evidence/2026-10-07_*.png (kept outside the repo).
Reproduce: `python -m scripts.live_smoke` (needs ~/.paypal/sandbox.env), then buy on
/store/<item> with the sandbox buyer, then POST /ship.
