from __future__ import annotations

import asyncio
import os

from order_routing.provider_policy import ProviderPolicyClient


async def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("Set INFRAI_API_KEY before running the example")

    client = ProviderPolicyClient(api_key)
    try:
        decision = await client.exclude_provider("receipts", "vendor-to-exclude")
        print(
            f"Applied receipts policy: excluded={decision.excluded_provider}; "
            f"capability={decision.capability}"
        )
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

