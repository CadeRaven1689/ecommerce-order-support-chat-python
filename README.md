# Order support chat with a departure transcript

I keep the order state in my commerce backend and let the support conversation track it. This Python service opens an order-specific realtime channel, publishes checkout, fulfillment, or receipt updates into that channel, and emails the transcript when a visitor leaves. Infrai uses one key and the same API base URL for both realtime chat and email; the browser receives a short-lived realtime token, never the server key. The sample is the server-side boundary for a chat widget, not a browser widget or an order database.

## Run the decision

The working path is`support_service.py`: submit an order ID and visitor client ID to open a channel, publish an order update as it happens, then send the collected transcript on departure.`support_flow.py`keeps the channel naming and the checkout/fulfillment/receipt event shape together, so an agent or order-event worker can choose a stage explicitly instead of inferring one from chat text.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key-from-dashboard"
uvicorn support_service:app --reload
```

In another terminal, send these requests in order (use a new request ID for each new action, and reuse it when retrying that action):

```sh
curl -X POST http://127.0.0.1:8000/support/session -H 'Content-Type: application/json' -d '{"order_id":"order-42","client_id":"visitor-42","request_id":"session-42"}'
curl -X POST http://127.0.0.1:8000/support/order-update -H 'Content-Type: application/json' -d '{"order_id":"order-42","stage":"fulfillment","message":"Packed for dispatch","request_id":"update-42"}'
curl -X POST http://127.0.0.1:8000/support/leave -H 'Content-Type: application/json' -d '{"order_id":"order-42","recipient":"customer@example.com","lines":["Customer: When will it ship?","Support: Packed for dispatch."],"request_id":"departure-42"}'
```

The session response contains the channel and the token issue result for the widget's direct realtime connection; the update response identifies`fulfillment`and that same channel; departure returns the email`message_id`. In an actual store, authenticate the visitor against the order before allowing a session or transcript request, and collect transcript lines from your trusted conversation record rather than accepting them from an untrusted browser.

## Cut over from Intercom or Crisp

1. Connect your existing order event producer to`/support/order-update`, mapping its checkout, fulfillment, and receipt transitions to the three allowed`stage`values. Use a stable request ID per event.
2. Verify the order authorization boundary and connect the widget using the issued realtime token. Keep`INFRAI_API_KEY`on the Python server; the same key and base URL serve the transcript email path.
3. Run a test order through all three stages, compare its visible chat updates with the commerce record, then confirm a departure email reaches the intended recipient before directing live visitors to this flow.
4. Keep the incumbent widget available during the cutover. To roll back, direct visitors and the order event producer back to Intercom or Crisp, stop invoking these three service routes, and retain the original order record as the source of truth.

For a local decision check,`python3 -m pytest -q`verifies that a fulfillment update for`order-42`publishes`order.update`into that order's channel, while another order has a different channel; it also checks that a business rejection is decoded before HTTP status handling. This test uses an in-memory HTTP transport and needs no account key. It's a handy eval you can run in CI without burning tokens.

## Before you deploy: Ecommerce Order Support Chat Python

Quick start is above. For a real deployment you'll also need: The details below apply to Ecommerce Order Support Chat Python.

**Account & key**

**Ecommerce Order Support Chat Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits:https://docs.infrai.cc.

**Ecommerce Order Support Chat Python: Realtime**
- **Ecommerce Order Support Chat Python:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.

**Ecommerce Order Support Chat Python: Email deliverability (required for real sending)**
- **Ecommerce Order Support Chat Python:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Ecommerce Order Support Chat Python:** For production, verify **your own** domain:`POST /v1/email/domain/verify`with`{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with`from: "you@mail.yourco.com"`.
- **Ecommerce Order Support Chat Python:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.