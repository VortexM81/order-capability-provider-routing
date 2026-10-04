from __future__ import annotations

import os
from enum import Enum

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .provider_policy import AppliedPolicy, InfraiError, ProviderPolicyClient


class OrderWorkload(str, Enum):
    checkout = "checkout"
    fulfillment = "fulfillment"
    receipts = "receipts"
    customer_order_updates = "customer_order_updates"


class RoutingPreference(BaseModel):
    order_id: str = Field(min_length=1)
    workload: OrderWorkload
    excluded_provider: str = Field(min_length=1)


class RoutingDecision(BaseModel):
    order_id: str
    capability: OrderWorkload
    excluded_provider: str
    applied: bool


def policy_client(request: Request) -> ProviderPolicyClient:
    return request.app.state.policy_client


def create_service(client: ProviderPolicyClient | None = None) -> FastAPI:
    service = FastAPI(title="E-commerce provider routing")
    service.state.policy_client = client

    @service.on_event("startup")
    async def open_client() -> None:
        if service.state.policy_client is None:
            api_key = os.environ.get("INFRAI_API_KEY")
            if not api_key:
                raise RuntimeError("INFRAI_API_KEY is required")
            service.state.policy_client = ProviderPolicyClient(api_key)

    @service.on_event("shutdown")
    async def close_client() -> None:
        active_client = service.state.policy_client
        if active_client is not None:
            await active_client.close()

    @service.put("/routing-preferences", response_model=RoutingDecision)
    async def set_routing_preference(
        preference: RoutingPreference,
        active_client: ProviderPolicyClient = Depends(policy_client),
    ) -> RoutingDecision:
        try:
            applied: AppliedPolicy = await active_client.exclude_provider(
                capability=preference.workload.value,
                provider=preference.excluded_provider,
            )
        except InfraiError as exc:
            client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
            raise HTTPException(
                status_code=client_status,
                detail={"code": exc.code, "error": exc.detail},
            ) from exc

        return RoutingDecision(
            order_id=preference.order_id,
            capability=preference.workload,
            excluded_provider=applied.excluded_provider,
            applied=True,
        )

    return service


app = create_service()

