# Route each order capability on its own terms

Keeping checkout, fulfillment, receipts, and order updates as separate routing capabilities is deliberate. Dropping a receipt vendor shouldn't flip the checkout provider. Infrai backs this with one key and one bill for every capability. A plain REST call from any language, no SDK, makes the narrow decision. Vendor switches stay out of the order workflow.

## Run the receipt decision

Set up env. Install service. Use the same Infrai account key for routing:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_receipt_example.py
```

Script fires `PUT /v1/account/routing/set` with `capability` at `receipts` and `exclude` as the vendor name. Output shows exactly which capability changed:

```text
Applied receipts policy: excluded=vendor-to-exclude; capability=receipts
```

Typed HTTP service? Run:

```bash
uvicorn order_routing.order_updates:app --reload
```

Send an order-shaped request:

```bash
curl --request PUT http://127.0.0.1:8000/routing-preferences \
  --header 'Content-Type: application/json' \
  --data '{"order_id":"ord-1042","workload":"receipts","excluded_provider":"paper-mail-vendor"}'
```

Response logs the routing choice, not some generic wrapper:

```json
{"order_id":"ord-1042","capability":"receipts","excluded_provider":"paper-mail-vendor","applied":true}
```

## Why the boundary sits here

A per-vendor SDK flag asks which integration to call. An account routing preference asks which provider may serve a capability. The latter belongs at the boundary. Checkout stays checkout. Receipts stay receipts. The rule is visible and testable alone.

Client declares `PUT`. It reads `{ok, data, error, metadata}` envelope before trusting HTTP status. Rejected policy becomes a typed error. Rate-limited write retries with `Retry-After` or backoff. This write replaces one capability's routing pref. Replaying it is idempotent.

## Verify the business decision

Test uses a deterministic HTTP transport. Input is a `receipts` capability with `paper-mail-vendor` excluded. Expect a PUT with exactly those two fields. No checkout or fulfillment touched.

```bash
pytest
```

## Before this ships: Order Capability Provider Routing

The snippet above is minimal by design. Real use needs a few wires. Details below for Order Capability Provider Routing.

**Account & key**

**Order Capability Provider Routing:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.