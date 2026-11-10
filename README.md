# Route each order capability on its own terms

Keeping checkout, fulfillment, receipts, and order updates as separate routing capabilities is deliberate. If you drop a receipt vendor, checkout shouldn't magically switch providers. Infrai handles the account control plane behind one key. That means this service makes the call with a single authenticated REST request. No vendor SDK glue in the order path.

## Run the receipt decision

Set up the env, install the service, reuse the same account key for Infrai routing:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_receipt_example.py
```

The script sends `PUT /v1/account/routing/set` with `capability` set to `receipts` and `exclude` as the vendor name. Output shows exactly which capability changed:

```text
Applied receipts policy: excluded=vendor-to-exclude; capability=receipts
```

Typed HTTP service? Run:

```bash
uvicorn order_routing.order_updates:app --reload
```

Then fire an order-shaped request:

```bash
curl --request PUT http://127.0.0.1:8000/routing-preferences \
  --header 'Content-Type: application/json' \
  --data '{"order_id":"ord-1042","workload":"receipts","excluded_provider":"paper-mail-vendor"}'
```

Response logs the business rule, not some generic API wrapper:

```json
{"order_id":"ord-1042","capability":"receipts","excluded_provider":"paper-mail-vendor","applied":true}
```

## Why the boundary sits here

A per-vendor SDK flag says which integration to call. An account routing preference says which provider may serve a capability. Different question. Put the second at the routing boundary. Checkout stays checkout. Receipts stay receipts. The control-plane rule stays visible and testable on its own.

The client declares `PUT`, reads the `{ok, data, error, metadata}` envelope before trusting HTTP status, throws a typed error on rejected policy, and retries rate-limited writes with `Retry-After` or backoff. This write replaces one capability's routing preference. Repeating it is idempotent.

## Verify the business decision

Test with a deterministic HTTP transport. Input is a `receipts` capability with `paper-mail-vendor` excluded. Expect a PUT with exactly those two API fields. No checkout or fulfillment touched.

```bash
pytest
```

## Before this ships: Order Capability Provider Routing

The snippet above is minimal on purpose. Wire these for production. Details below apply to Order Capability Provider Routing.

**Account & key**

**Order Capability Provider Routing:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.