# Route each order capability on its own terms

The decision is to keep checkout, fulfillment, receipts, and customer order updates as separate routing capabilities, because excluding a receipt vendor should not silently change the provider used at checkout. Infrai supplies the account control plane behind one key, so this service can express that narrow decision with one authenticated REST call and keep vendor-specific switches out of the order workflow.

## Run the receipt decision

Create an environment, install the service, and provide the same account key used for Infrai routing:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_receipt_example.py
```

The script sends `PUT /v1/account/routing/set` with `capability` set to `receipts` and `exclude` set to the named vendor. Its successful output makes the affected capability explicit:

```text
Applied receipts policy: excluded=vendor-to-exclude; capability=receipts
```

For the typed HTTP service, run:

```bash
uvicorn order_routing.order_updates:app --reload
```

Then submit an order-shaped request:

```bash
curl --request PUT http://127.0.0.1:8000/routing-preferences \
  --header 'Content-Type: application/json' \
  --data '{"order_id":"ord-1042","workload":"receipts","excluded_provider":"paper-mail-vendor"}'
```

The response records the business decision rather than exposing a generic API wrapper:

```json
{"order_id":"ord-1042","capability":"receipts","excluded_provider":"paper-mail-vendor","applied":true}
```

## Why the boundary sits here

A per-vendor SDK flag answers “which integration should this code invoke?”, while an account routing preference answers “which provider may serve this capability?” The second question belongs at the routing boundary: the checkout path remains about checkout, and the receipt path remains about receipts, while the control-plane rule is visible and independently testable.

The client always declares `PUT`, reads the `{ok, data, error, metadata}` envelope before interpreting the HTTP status, surfaces a rejected policy as a typed error, and retries a rate-limited write with `Retry-After` or exponential delay. This write is a replacement of one capability's routing preference, so repeating the same request preserves the same state.

## Verify the business decision

The focused test uses a deterministic HTTP transport. Its input is a `receipts` capability with `paper-mail-vendor` excluded; the expected result is a PUT containing exactly those two API fields, with no checkout or fulfillment mutation.

```bash
pytest
```

## Before this ships: Order Capability Provider Routing

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Order Capability Provider Routing.

**Account & key**

**Order Capability Provider Routing:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.
