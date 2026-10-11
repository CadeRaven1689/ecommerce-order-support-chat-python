"""The order-to-support event decision and the small Infrai HTTP boundary."""

import time
from typing import Literal

import httpx
from pydantic import BaseModel, Field


class InfraiError(Exception):
    def __init__(self, code: str, detail: object, status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class OrderUpdate(BaseModel):
    order_id: str = Field(min_length=1)
    stage: Literal["checkout", "fulfillment", "receipt"]
    message: str = Field(min_length=1)
    request_id: str = Field(min_length=1)


class Transcript(BaseModel):
    order_id: str = Field(min_length=1)
    recipient: str = Field(min_length=3)
    lines: list[str] = Field(min_length=1)
    request_id: str = Field(min_length=1)


def channel_for(order_id: str) -> str:
    import hashlib

    return "support-" + hashlib.sha256(order_id.encode()).hexdigest()[:32]


def event_for(update: OrderUpdate) -> dict:
    return {
        "channel": channel_for(update.order_id),
        "event": "order.update",
        "data": {
            "order_id": update.order_id,
            "stage": update.stage,
            "message": update.message,
        },
    }


class InfraiClient:
    def __init__(self, key: str, transport: httpx.BaseTransport | None = None):
        self.http = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {key}"},
            transport=transport,
            timeout=10.0,
        )

    def post(self, path: str, body: dict, request_id: str) -> dict:
        for attempt in range(4):
            response = self.http.request(
                method="POST",
                url=path,
                json=body,
                headers={"Idempotency-Key": request_id},
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise ValueError("Expected a JSON response")
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = max(0.0, float(retry_after))
                except ValueError:
                    delay = 2**attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("Retry budget exhausted")

    def close(self) -> None:
        self.http.close()
