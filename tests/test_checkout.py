"""Checkout state machine: live item -> PayPal order -> capture -> paid -> shipped.

Uses a FakePayPal double so the money path is exercised with zero network.
"""
import time

import pytest

from shelf import checkout, store
from shelf.paypal import PayPalError


class FakePayPal:
    def __init__(self):
        self.orders: dict[str, dict] = {}
        self.captures: list[str] = []
        self.tracks: list[dict] = []
        self.fail_capture = False

    async def create_order(self, **kw):
        oid = f"ORD{len(self.orders) + 1}"
        self.orders[oid] = kw
        return {"id": oid, "status": "CREATED", "approve_url": f"https://sandbox.test/approve/{oid}", "raw": {}}

    async def get_order(self, order_id):
        return {"id": order_id, "status": "APPROVED"}

    async def capture_order(self, order_id):
        if self.fail_capture:
            raise PayPalError("POST capture -> 422 UNPROCESSABLE_ENTITY INSTRUMENT_DECLINED",
                              status_code=422, debug_id="dbg")
        self.captures.append(order_id)
        kw = self.orders[order_id]
        return {"order_id": order_id, "status": "COMPLETED", "capture_id": f"CAP-{order_id}",
                "capture_status": "COMPLETED", "amount": kw["amount"], "net_amount": "0.00",
                "currency": "USD", "custom_id": kw["custom_id"], "payer_email": "buyer@example.com",
                "payer_id": "P1", "raw": {}}

    async def add_tracking(self, order_id, *, capture_id, tracking_number, carrier="USPS", notify_payer=True):
        self.tracks.append({"order_id": order_id, "capture_id": capture_id,
                            "tracking_number": tracking_number, "carrier": carrier})
        return {"order_id": order_id, "tracker_id": f"{capture_id}-{tracking_number}", "raw": {}}


@pytest.fixture
def st(tmp_path):
    return store.LocalJSONStore(str(tmp_path))


@pytest.fixture
def pp():
    return FakePayPal()


def _live(st, item_id="it_1", price=45.0, title="Framed print"):
    it = store.Item(id=item_id, created=time.time(), photo_paths=[], status="live",
                    curator={}, appraiser={}, copywriter={}, title=title,
                    description="A print. Small scuff on frame.", tags=[], price=price, floor=30.0)
    st.save_item(it)
    return it


def test_money_formatting():
    assert checkout.money(45) == "45.00"
    assert checkout.money(45.5) == "45.50"
    assert checkout.money(0.1 + 0.2) == "0.30"
    assert checkout.money(1234.567) == "1234.57"


async def test_start_checkout_creates_order_from_item_price(st, pp):
    _live(st)
    res = await checkout.start_checkout(st, pp, "it_1", public_url="https://shelf.test")
    assert res["order_id"] == "ORD1"
    assert res["approve_url"].endswith("/approve/ORD1")
    kw = pp.orders["ORD1"]
    assert kw["amount"] == "45.00"
    assert kw["custom_id"] == "it_1"
    assert kw["description"].startswith("Framed print")
    assert kw["items"][0]["name"] == "Framed print"
    assert kw["return_url"] == "https://shelf.test/store/it_1?paid=1"
    assert kw["cancel_url"] == "https://shelf.test/store/it_1"
    item = st.get_item("it_1")
    assert item.paypal_order_id == "ORD1"
    assert item.status == "live"  # still live until money lands


async def test_start_checkout_refuses_non_live_item(st, pp):
    it = _live(st)
    it.status = "draft"
    st.save_item(it)
    with pytest.raises(ValueError):
        await checkout.start_checkout(st, pp, "it_1", public_url="https://shelf.test")


async def test_start_checkout_refuses_zero_price(st, pp):
    _live(st, price=0.0)
    with pytest.raises(ValueError):
        await checkout.start_checkout(st, pp, "it_1", public_url="https://shelf.test")


async def test_complete_checkout_captures_and_books(st, pp):
    _live(st)
    await checkout.start_checkout(st, pp, "it_1", public_url="https://shelf.test")
    item = await checkout.complete_checkout(st, pp, "ORD1")
    assert item.status == "paid"
    assert item.paypal_capture_id == "CAP-ORD1"
    assert item.sold_price == 45.0
    assert item.buyer_email == "buyer@example.com"
    ledger = st.list_ledger()
    kinds = sorted(e.kind for e in ledger)
    assert kinds == ["paid"]
    paid = ledger[0]
    assert paid.paypal_capture_id == "CAP-ORD1"
    assert paid.amount == 45.0
    assert paid.item_id == "it_1"
    assert st.totals()["paid_total"] == 45.0
    assert st.totals()["sold_count"] == 1


async def test_complete_checkout_is_idempotent(st, pp):
    _live(st)
    await checkout.start_checkout(st, pp, "it_1", public_url="https://shelf.test")
    await checkout.complete_checkout(st, pp, "ORD1")
    item = await checkout.complete_checkout(st, pp, "ORD1")  # second popup callback / webhook replay
    assert item.status == "paid"
    assert len(st.list_ledger()) == 1
    assert pp.captures == ["ORD1"]  # no second capture call


async def test_complete_checkout_declined_leaves_item_live(st, pp):
    _live(st)
    await checkout.start_checkout(st, pp, "it_1", public_url="https://shelf.test")
    pp.fail_capture = True
    with pytest.raises(PayPalError):
        await checkout.complete_checkout(st, pp, "ORD1")
    item = st.get_item("it_1")
    assert item.status == "live"
    assert item.paypal_capture_id == ""
    assert st.list_ledger() == []


async def test_record_capture_from_webhook_without_prior_order_lookup(st, pp):
    """A PAYMENT.CAPTURE.COMPLETED webhook carries custom_id; booking must work from it alone."""
    _live(st)
    summary = {"order_id": "ORDX", "status": "COMPLETED", "capture_id": "CAPX", "capture_status": "COMPLETED",
               "amount": "45.00", "net_amount": "43.39", "currency": "USD", "custom_id": "it_1",
               "payer_email": "b@example.com", "payer_id": "P", "raw": {}}
    item = checkout.record_capture(st, summary)
    assert item.status == "paid"
    assert item.paypal_capture_id == "CAPX"
    assert item.net_amount == 43.39
    # replay is a no-op
    checkout.record_capture(st, summary)
    assert len(st.list_ledger()) == 1


def test_record_capture_unknown_item_returns_none(st):
    summary = {"order_id": "O", "status": "COMPLETED", "capture_id": "C", "capture_status": "COMPLETED",
               "amount": "1.00", "net_amount": "", "currency": "USD", "custom_id": "it_nope",
               "payer_email": "", "payer_id": "", "raw": {}}
    assert checkout.record_capture(st, summary) is None


async def test_ship_item_adds_tracking_and_marks_shipped(st, pp):
    _live(st)
    await checkout.start_checkout(st, pp, "it_1", public_url="https://shelf.test")
    await checkout.complete_checkout(st, pp, "ORD1")
    item = await checkout.ship_item(st, pp, "it_1", tracking_number="9400 1000 0000", carrier="USPS")
    assert item.status == "shipped"
    assert item.tracking_number == "940010000000"
    assert item.carrier == "USPS"
    assert pp.tracks == [{"order_id": "ORD1", "capture_id": "CAP-ORD1",
                          "tracking_number": "940010000000", "carrier": "USPS"}]
    kinds = sorted(e.kind for e in st.list_ledger())
    assert kinds == ["paid", "shipped"]


async def test_ship_item_requires_paid(st, pp):
    _live(st)
    with pytest.raises(ValueError):
        await checkout.ship_item(st, pp, "it_1", tracking_number="1", carrier="USPS")
