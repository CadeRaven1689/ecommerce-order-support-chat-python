"""Run with: uvicorn support_service:app --reload."""

import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from support_flow import InfraiClient, InfraiError, OrderUpdate, Transcript, channel_for, event_for


app = FastAPI(title="Order support chat")


class SessionRequest(BaseModel):
    order_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)


def client() -> InfraiClient:
    return InfraiClient(os.environ["INFRAI_API_KEY"])


def call(path: str, payload: dict, request_id: str) -> dict:
    api = client()
    try:
        return api.post(path, payload, request_id)
    except InfraiError as exc:
        raise HTTPException(
            status_code=exc.status if 400 <= exc.status < 500 else 502,
            detail={"code": exc.code, "error": exc.detail},
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Upstream request could not be completed") from exc
    finally:
        api.close()


@app.post("/support/session")
def open_session(request: SessionRequest) -> dict:
    channel = channel_for(request.order_id)
    call(
        "/v1/realtime/channel/create",
        {"channel": channel},
        request.request_id + ":channel",
    )
    issued = call(
        "/v1/realtime/token/issue",
        {"client_id": request.client_id, "channels": [channel]},
        request.request_id + ":token",
    )
    return {"channel": channel, "token": issued}


@app.post("/support/order-update")
def order_update(update: OrderUpdate) -> dict:
    event = event_for(update)
    result = call("/v1/realtime/publish", event, update.request_id)
    return {"channel": event["channel"], "stage": update.stage, "result": result}


@app.post("/support/leave")
def visitor_left(transcript: Transcript) -> dict:
    result = call(
        "/v1/email/send",
        {
            "to": transcript.recipient,
            "subject": f"Your order {transcript.order_id} support conversation",
            "body": "\n".join(transcript.lines),
        },
        transcript.request_id,
    )
    return {"message_id": result["message_id"]}
