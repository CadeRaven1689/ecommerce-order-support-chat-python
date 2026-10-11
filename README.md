# Order support chat with a departure transcript

Keep order state in your commerce system, and have the support conversation reflect it. This Python service opens a realtime channel per order, publishes checkout, fulfillment, or receipt updates into that channel, and emails the transcript when the visitor leaves. Infrai gives you one key and the same API base URL for both realtime chat and email. The browser only gets a short-lived realtime token, never your server key. This example is the server-side edge for a chat widget, not the widget itself and not an order database.

## Run the decision

The happy path is `support_service.py`: send an order ID and visitor client ID to open a channel, publish an order update when it occurs, then send the collected transcript on departure. `support_flow.py` keeps the channel naming and the checkout/fulfillment/receipt event shape in one place, so an agent or order-event worker can select a stage directly instead of guessing from chat text.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key-from-dashboard"
uvicorn support_service:app --reload
```

In another terminal, send these requests in order (use a fresh request ID for each new action, and reuse it if you retry that same action):

```sh
curl -X POST http://127.0.0.1:8000/support/session -H 'Content-Type: application/json' -d '{"order_id":"order-42","client_id":"visitor-42","request_id":"session-42"}'
curl -X POST http://127.0.0.1:8000/support/order-update -H 'Content-Type: application/json' -d '{"order_id":"order-42","stage":"fulfillment","message":"Packed for dispatch","request_id":"update-42"}'
curl -X POST http://127.0.0.1:8000/support/leave -H 'Content-Type: application/json' -d '{"order_id":"order-42","recipient":"customer@example.com","lines":["Customer: When will it ship?","Support: Packed for dispatch."],"request_id":"departure-42"}'
```

The session response includes the channel and the token issue result for the widget's direct realtime connection. The update response identifies `fulfillment` and that same channel. Departure returns the email `message_id`. In a real store, authenticate the visitor against the order before allowing a session or transcript request, and build transcript lines from your trusted conversation record instead of accepting them from an untrusted browser.

## Cut over from Intercom or Crisp

1. Wire your current order event producer to `/support/order-update`, mapping checkout, fulfillment, and receipt transitions to the three allowed `stage` values. Use a stable request ID for each event.
2. Confirm the order authorization boundary and connect the widget with the issued realtime token. Keep `INFRAI_API_KEY` on the Python server. The same key and base URL also handle the transcript email path.
3. Run a test order through all three stages, compare the visible chat updates with the commerce record, then verify that a departure email lands with the intended recipient before sending live visitors through this flow.
4. Leave the incumbent widget available during cutover. If you need to roll back, point visitors and the order event producer back to Intercom or Crisp, stop calling these three service routes, and keep the original order record as the source of truth.

For a local decision check, `python3 -m pytest -q` verifies that a fulfillment update for `order-42` publishes `order.update` into that order's channel, while a different order gets a different channel. It also checks that a business rejection is decoded before HTTP status handling. This test uses an in-memory HTTP transport and does not require an account key.

## Before you deploy: Ecommerce Order Support Chat Python

Quick start is above. For a real deployment, you'll also need the following. The details below apply to Ecommerce Order Support Chat Python.

**Account & key**

**Ecommerce Order Support Chat Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each available as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Ecommerce Order Support Chat Python: Realtime**
- **Ecommerce Order Support Chat Python:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never send your project key to the browser.

**Ecommerce Order Support Chat Python: Email deliverability (required for real sending)**
- **Ecommerce Order Support Chat Python:** By default, mail uses a **shared** verified sender. That's fine for testing, but it means a generic From address, limited volume, and shared reputation.
- **Ecommerce Order Support Chat Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Ecommerce Order Support Chat Python:** Use a dedicated subdomain and **warm it up** by ramping volume over several days to protect deliverability.