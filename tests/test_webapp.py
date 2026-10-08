"""HTTP layer tests: PayPal config, order create, capture, webhook, ship, item page."""
import json
import time

import pytest
from fastapi.testclient import TestClient

from shelf import store as store_mod
from shelf.webapp import create_app
from tests.test_checkout import FakePayPal


@pytest.fixture
def st(tmp_path):
    return store_mod.LocalJSONStore(str(tmp_path))


@pytest.fixture
def pp():
    return FakePayPal()


@pytest.fixture
def client(st, pp, monkeypatch, tmp_path):
    monkeypatch.setenv("PUBLIC_URL", "https://shelf.test")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "browser-safe-id")
    monkeypatch.delenv("SHELF_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("PAYPAL_WEBHOOK_ID", raising=False)
    monkeypatch.chdir(tmp_path)
    app = create_app(store=st, paypal=pp)
    return TestClient(app)


def _live(st, item_id="it_1", price=45.0):
    it = store_mod.Item(id=item_id, created=time.time(), photo_paths=[], status="live",
                        curator={}, appraiser={}, copywriter={}, title="Framed print",
                        description="A print.", tags=[], price=price, floor=30.0)
    st.save_item(it)
    return it


def test_paypal_config_exposes_client_id_and_sandbox_flag(client):
    r = client.get("/api/paypal/config")
    assert r.status_code == 200
    j = r.json()
    assert j["enabled"] is True
    assert j["client_id"] == "browser-safe-id"
    assert j["sandbox"] is True
    assert j["currency"] == "USD"


def test_paypal_config_disabled_without_client(st, monkeypatch, tmp_path):
    monkeypatch.delenv("PAYPAL_CLIENT_ID", raising=False)
    monkeypatch.chdir(tmp_path)
    c = TestClient(create_app(store=st, paypal=None))
    j = c.get("/api/paypal/config").json()
    assert j["enabled"] is False


def test_create_order_route(client, st, pp):
    _live(st)
    r = client.post("/api/paypal/orders", json={"item_id": "it_1"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["id"] == "ORD1"
    assert j["approve_url"].endswith("/approve/ORD1")
    assert pp.orders["ORD1"]["return_url"] == "https://shelf.test/store/it_1?paid=1"


def test_create_order_route_rejects_draft(client, st):
    it = _live(st)
    it.status = "draft"
    st.save_item(it)
    r = client.post("/api/paypal/orders", json={"item_id": "it_1"})
    assert r.status_code == 409


def test_capture_route_books_sale(client, st, pp):
    _live(st)
    client.post("/api/paypal/orders", json={"item_id": "it_1"})
    r = client.post("/api/paypal/orders/ORD1/capture")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] == "COMPLETED"
    assert j["capture_id"] == "CAP-ORD1"
    assert j["item"]["status"] == "paid"
    assert st.get_item("it_1").status == "paid"


def test_capture_route_declined_returns_402(client, st, pp):
    _live(st)
    client.post("/api/paypal/orders", json={"item_id": "it_1"})
    pp.fail_capture = True
    r = client.post("/api/paypal/orders/ORD1/capture")
    assert r.status_code == 402
    assert "INSTRUMENT_DECLINED" in r.json()["detail"]
    assert st.get_item("it_1").status == "live"


def test_webhook_capture_completed_books_sale_when_unverified_allowed(client, st, monkeypatch):
    monkeypatch.setenv("SHELF_ALLOW_UNVERIFIED_WEBHOOKS", "1")
    _live(st)
    event = {
        "id": "WH-1", "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {"id": "CAP-WH", "status": "COMPLETED", "custom_id": "it_1",
                     "amount": {"currency_code": "USD", "value": "45.00"},
                     "seller_receivable_breakdown": {"net_amount": {"currency_code": "USD", "value": "43.39"}},
                     "supplementary_data": {"related_ids": {"order_id": "ORD-WH"}}},
    }
    r = client.post("/api/paypal/webhook", content=json.dumps(event),
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 200, r.text
    assert r.json()["handled"] is True
    it = st.get_item("it_1")
    assert it.status == "paid"
    assert it.paypal_capture_id == "CAP-WH"
    assert it.paypal_order_id == "ORD-WH"
    assert it.net_amount == 43.39


def test_webhook_rejected_when_unverifiable(client, st, monkeypatch):
    monkeypatch.delenv("SHELF_ALLOW_UNVERIFIED_WEBHOOKS", raising=False)
    _live(st)
    r = client.post("/api/paypal/webhook", json={"event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {}})
    assert r.status_code == 400


def test_webhook_ignores_other_events(client, monkeypatch):
    monkeypatch.setenv("SHELF_ALLOW_UNVERIFIED_WEBHOOKS", "1")
    r = client.post("/api/paypal/webhook", json={"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {}})
    assert r.status_code == 200
    assert r.json()["handled"] is False


def test_ship_route(client, st, pp):
    _live(st)
    client.post("/api/paypal/orders", json={"item_id": "it_1"})
    client.post("/api/paypal/orders/ORD1/capture")
    r = client.post("/api/items/it_1/ship", json={"tracking_number": "9400 1", "carrier": "usps"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "shipped"
    assert pp.tracks[0]["tracking_number"] == "94001"
    assert pp.tracks[0]["carrier"] == "USPS"


def test_admin_token_guards_approve_and_ship(st, pp, monkeypatch, tmp_path):
    monkeypatch.setenv("SHELF_ADMIN_TOKEN", "s3cret")
    monkeypatch.chdir(tmp_path)
    c = TestClient(create_app(store=st, paypal=pp))
    it = _live(st)
    it.status = "draft"
    st.save_item(it)
    assert c.post("/api/items/it_1/approve").status_code == 401
    assert c.post("/api/items/it_1/approve", headers={"X-Shelf-Admin": "nope"}).status_code == 401
    r = c.post("/api/items/it_1/approve", headers={"X-Shelf-Admin": "s3cret"})
    assert r.status_code == 200
    assert st.get_item("it_1").status == "live"
    # buyers never need the token
    assert c.post("/api/paypal/orders", json={"item_id": "it_1"}).status_code == 200


def test_item_page_and_api(client, st):
    _live(st)
    r = client.get("/store/it_1")
    assert r.status_code == 200
    assert "paypal-button" in r.text
    j = client.get("/api/store-items/it_1").json()
    assert j["id"] == "it_1"
    assert j["title"] == "Framed print"
    assert j["status"] == "live"
    assert client.get("/store/it_missing").status_code == 404


def test_store_items_includes_sold_flag_for_paid(client, st, pp):
    _live(st)
    client.post("/api/paypal/orders", json={"item_id": "it_1"})
    client.post("/api/paypal/orders/ORD1/capture")
    items = client.get("/api/store-items").json()
    assert items == []  # live only on the grid
    j = client.get("/api/store-items/it_1").json()
    assert j["status"] == "paid"


def test_ledger_api_carries_paypal_ids(client, st, pp):
    _live(st)
    client.post("/api/paypal/orders", json={"item_id": "it_1"})
    client.post("/api/paypal/orders/ORD1/capture")
    j = client.get("/api/ledger").json()
    assert j["totals"]["paid_total"] == 45.0
    assert j["entries"][0]["paypal_capture_id"] == "CAP-ORD1"
    assert j["entries"][0]["kind"] == "paid"
