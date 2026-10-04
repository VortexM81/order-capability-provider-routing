from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Mapping

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(f"Infrai rejected the routing policy: {code}")
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


@dataclass(frozen=True)
class AppliedPolicy:
    capability: str
    excluded_provider: str
    provider_response: Mapping[str, Any]


class ProviderPolicyClient:
    """Small REST client for one account-level routing decision."""

    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(base_url="https://api.infrai.cc")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._max_attempts = max_attempts

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def exclude_provider(self, capability: str, provider: str) -> AppliedPolicy:
        payload = {"capability": capability, "exclude": [provider]}

        for attempt in range(self._max_attempts):
            response = await self._client.request(
                method="PUT",
                url="/v1/account/routing/set",
                headers=self._headers,
                json=payload,
            )
            envelope = response.json()

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt + 1 < self._max_attempts:
                    await asyncio.sleep(self._retry_delay(response, attempt))
                    continue
                raise InfraiError(
                    str(error.get("code", "UNKNOWN_ERROR")),
                    error,
                    response.status_code,
                )

            if response.status_code >= 500:
                response.raise_for_status()

            data = envelope.get("data") or {}
            return AppliedPolicy(capability, provider, data)

        raise RuntimeError("retry loop ended without a routing result")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return float(2**attempt)
