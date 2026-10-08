"""PayPalClient unit tests against a fake sandbox (respx). No network, no keys."""
import base64
import json

import httpx
import pytest
import respx

from shelf.paypal import PayPalClient, PayPalError

BASE = "https://api-m.sandbox.paypal.com"


@pytest.fixture
def client() -> PayPalClient:
    return PayPalClient(client_id="cid", secret="sec", base_url=BASE)


def _token_route(mock: respx.MockRouter, token: str = "tok1", expires: int = 3600):
    return mock.post(f"{BASE}/v1/oauth2/token").mock(
        return_value=httpx.Response(200, json={"access_token": token, "expires_in": expires})
    )


@respx.mock
async def test_token_uses_basic_auth_and_client_credentials(client):
    route = _token_route(respx)
    tok = await client.access_token()
    assert tok == "tok1"
    req = route.calls[0].request
    expected = "Basic " + base64.b64encode(b"cid:sec").decode()
    assert req.headers["authorization"] == expected
    assert req.content == b"grant_type=client_credentials"


@respx.mock
async def test_token_is_cached_until_expiry(client):
    route = _token_route(respx)
    await client.access_token()
    await client.access_token()
    assert route.call_count == 1


@respx.mock
async def test_create_order_sends_capture_intent_and_returns_id(client):
    _token_route(respx)
    route = respx.post(f"{BASE}/v2/checkout/orders").mock(
        return_value=httpx.Response(201, json={
            "id": "5O190127TN364715T", "status": "CREATED",
            "links": [{"href": f"{BASE}/v2/checkout/orders/5O190127TN364715T", "rel": "self", "method": "GET"},
                      {"href": "https://www.sandbox.paypal.com/checkoutnow?token=5O190127TN364715T",
                       "rel": "payer-action", "method": "GET"}],
        })
    )
    order = await client.create_order(
        amount="45.00", description="Framed print", custom_id="it_abc123",
        items=[{"name": "Framed print", "unit_amount": "45.00", "quantity": 1, "sku": "it_abc123"}],
        return_url="https://x.test/return", cancel_url="https://x.test/cancel", brand_name="SHELF",
    )
    assert order["id"] == "5O190127TN364715T"
    assert order["status"] == "CREATED"
    assert order["approve_url"] == "https://www.sandbox.paypal.com/checkoutnow?token=5O190127TN364715T"

    req = route.calls[0].request
    assert req.headers["authorization"] == "Bearer tok1"
    assert req.headers["content-type"] == "application/json"
    assert req.headers["paypal-request-id"]  # idempotency key present
    body = json.loads(req.content)
    assert body["intent"] == "CAPTURE"
    pu = body["purchase_units"][0]
    assert pu["amount"] == {"currency_code": "USD", "value": "45.00",
                            "breakdown": {"item_total": {"currency_code": "USD", "value": "45.00"}}}
    assert pu["custom_id"] == "it_abc123"
    assert pu["description"] == "Framed print"
    assert pu["items"][0] == {"name": "Framed print", "quantity": "1", "sku": "it_abc123",
                              "category": "PHYSICAL_GOODS",
                              "unit_amount": {"currency_code": "USD", "value": "45.00"}}
    ctx = body["payment_source"]["paypal"]["experience_context"]
    assert ctx["return_url"] == "https://x.test/return"
    assert ctx["cancel_url"] == "https://x.test/cancel"
    assert ctx["user_action"] == "PAY_NOW"
    assert ctx["brand_name"] == "SHELF"
    assert ctx["shipping_preference"] == "GET_FROM_FILE"


@respx.mock
async def test_capture_order_returns_capture_id_and_amount(client):
    _token_route(respx)
    respx.post(f"{BASE}/v2/checkout/orders/ORD1/capture").mock(
        return_value=httpx.Response(201, json={
            "id": "ORD1", "status": "COMPLETED",
            "payer": {"email_address": "buyer@example.com", "payer_id": "PAYER1"},
            "purchase_units": [{"custom_id": "it_abc123", "payments": {"captures": [
                {"id": "CAP1", "status": "COMPLETED",
                 "amount": {"currency_code": "USD", "value": "45.00"},
                 "seller_receivable_breakdown": {"net_amount": {"currency_code": "USD", "value": "43.39"}}}
            ]}}],
        })
    )
    cap = await client.capture_order("ORD1")
    assert cap["order_id"] == "ORD1"
    assert cap["status"] == "COMPLETED"
    assert cap["capture_id"] == "CAP1"
    assert cap["amount"] == "45.00"
    assert cap["net_amount"] == "43.39"
    assert cap["custom_id"] == "it_abc123"
    assert cap["payer_email"] == "buyer@example.com"


@respx.mock
async def test_capture_declined_raises_paypal_error(client):
    _token_route(respx)
    respx.post(f"{BASE}/v2/checkout/orders/ORD2/capture").mock(
        return_value=httpx.Response(422, json={"name": "UNPROCESSABLE_ENTITY",
                                               "details": [{"issue": "INSTRUMENT_DECLINED"}],
                                               "debug_id": "dbg123"})
    )
    with pytest.raises(PayPalError) as ei:
        await client.capture_order("ORD2")
    assert "INSTRUMENT_DECLINED" in str(ei.value)
    assert ei.value.debug_id == "dbg123"
    assert ei.value.status_code == 422


@respx.mock
async def test_get_order(client):
    _token_route(respx)
    respx.get(f"{BASE}/v2/checkout/orders/ORD1").mock(
        return_value=httpx.Response(200, json={"id": "ORD1", "status": "APPROVED"}))
    o = await client.get_order("ORD1")
    assert o["status"] == "APPROVED"


@respx.mock
async def test_add_tracking_posts_capture_id_and_number(client):
    _token_route(respx)
    route = respx.post(f"{BASE}/v2/checkout/orders/ORD1/track").mock(
        return_value=httpx.Response(201, json={"id": "ORD1", "status": "COMPLETED",
                                               "purchase_units": [{"shipping": {"trackers": [
                                                   {"id": "CAP1-9400111", "status": "SHIPPED"}]}}]}))
    res = await client.add_tracking("ORD1", capture_id="CAP1", tracking_number="9400111", carrier="USPS")
    body = json.loads(route.calls[0].request.content)
    assert body == {"capture_id": "CAP1", "tracking_number": "9400111", "carrier": "USPS", "notify_payer": True}
    assert res["tracker_id"] == "CAP1-9400111"


@respx.mock
async def test_401_refreshes_token_once_and_retries(client):
    tokens = iter(["old", "new"])
    respx.post(f"{BASE}/v1/oauth2/token").mock(
        side_effect=lambda req: httpx.Response(200, json={"access_token": next(tokens), "expires_in": 3600}))
    calls = {"n": 0}

    def order_side_effect(req):
        calls["n"] += 1
        if req.headers["authorization"] == "Bearer old":
            return httpx.Response(401, json={"error": "invalid_token"})
        return httpx.Response(200, json={"id": "ORD1", "status": "CREATED"})

    respx.get(f"{BASE}/v2/checkout/orders/ORD1").mock(side_effect=order_side_effect)
    o = await client.get_order("ORD1")
    assert o["status"] == "CREATED"
    assert calls["n"] == 2


def test_from_env_reads_sandbox_by_default(monkeypatch):
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "a")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "b")
    monkeypatch.delenv("PAYPAL_ENVIRONMENT", raising=False)
    c = PayPalClient.from_env()
    assert c.base_url == BASE
    assert c.client_id == "a"
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", "PRODUCTION")
    assert PayPalClient.from_env().base_url == "https://api-m.paypal.com"


def test_from_env_returns_none_without_credentials(monkeypatch):
    monkeypatch.delenv("PAYPAL_CLIENT_ID", raising=False)
    monkeypatch.delenv("PAYPAL_CLIENT_SECRET", raising=False)
    assert PayPalClient.from_env() is None


@respx.mock
async def test_verify_webhook_posts_headers_and_event(client):
    _token_route(respx)
    route = respx.post(f"{BASE}/v1/notifications/verify-webhook-signature").mock(
        return_value=httpx.Response(200, json={"verification_status": "SUCCESS"}))
    headers = {"paypal-auth-algo": "SHA256withRSA", "paypal-cert-url": "https://api.sandbox.paypal.com/cert",
               "paypal-transmission-id": "t1", "paypal-transmission-sig": "sig", "paypal-transmission-time": "now"}
    ok = await client.verify_webhook(headers, {"id": "WH-1"}, webhook_id="WHID")
    assert ok is True
    body = json.loads(route.calls[0].request.content)
    assert body == {"auth_algo": "SHA256withRSA", "cert_url": "https://api.sandbox.paypal.com/cert",
                    "transmission_id": "t1", "transmission_sig": "sig", "transmission_time": "now",
                    "webhook_id": "WHID", "webhook_event": {"id": "WH-1"}}


@respx.mock
async def test_verify_webhook_failure_is_false(client):
    _token_route(respx)
    respx.post(f"{BASE}/v1/notifications/verify-webhook-signature").mock(
        return_value=httpx.Response(200, json={"verification_status": "FAILURE"}))
    assert await client.verify_webhook({}, {}, webhook_id="WHID") is False
