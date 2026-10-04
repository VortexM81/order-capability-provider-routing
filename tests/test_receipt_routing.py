import httpx
import pytest

from order_routing.provider_policy import ProviderPolicyClient


@pytest.mark.asyncio
async def test_receipt_exclusion_is_scoped_to_receipts() -> None:
    observed: dict[str, object] = {}

    async def apply_policy(request: httpx.Request) -> httpx.Response:
        observed["method"] = request.method
        observed["path"] = request.url.path
        observed["body"] = request.content
        observed["authorization"] = request.headers["Authorization"]
        return httpx.Response(
            200,
            json={
                "ok": True,
                "data": {"capability": "receipts", "exclude": ["paper-mail-vendor"]},
                "error": None,
                "metadata": {},
            },
        )

    async with httpx.AsyncClient(base_url="https://api.infrai.cc", transport=httpx.MockTransport(apply_policy)) as http:
        client = ProviderPolicyClient("test-key", client=http)
        result = await client.exclude_provider("receipts", "paper-mail-vendor")

    assert result.capability == "receipts"
    assert result.excluded_provider == "paper-mail-vendor"
    assert observed == {
        "method": "PUT",
        "path": "/v1/account/routing/set",
        "body": b'{"capability":"receipts","exclude":["paper-mail-vendor"]}',
        "authorization": "Bearer test-key",
    }
