import httpx

from support_flow import InfraiClient, InfraiError, OrderUpdate, channel_for, event_for


def test_fulfillment_update_targets_the_orders_chat() -> None:
    update = OrderUpdate(
        order_id="order-42", stage="fulfillment", message="Packed for dispatch", request_id="evt-42"
    )
    assert event_for(update) == {
        "channel": channel_for("order-42"),
        "event": "order.update",
        "data": {
            "order_id": "order-42",
            "stage": "fulfillment",
            "message": "Packed for dispatch",
        },
    }
    assert channel_for("order-42") != channel_for("order-43")


def test_business_rejection_is_read_before_http_status() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["Idempotency-Key"] == "evt-42"
        return httpx.Response(400, json={"ok": False, "error": {"code": "INVALID_ARGUMENT"}})

    api = InfraiClient("test-key", transport=httpx.MockTransport(respond))
    try:
        api.post("/v1/realtime/publish", {}, "evt-42")
    except InfraiError as error:
        assert error.code == "INVALID_ARGUMENT"
        assert error.status == 400
    else:
        raise AssertionError("Expected a business rejection")
    finally:
        api.close()
