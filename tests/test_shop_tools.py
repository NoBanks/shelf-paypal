"""Shopkeeper / bookkeeper tools against the fake PayPal double."""
import time

import pytest

from shelf import shop_tools, store as store_mod
from tests.test_checkout import FakePayPal


class FakePayPalWithOrders(FakePayPal):
    """get_order returns a capture-shaped raw order once captured, like the real API."""

    async def get_order(self, order_id):
        kw = self.orders.get(order_id)
        if kw is None:
            from shelf.paypal import PayPalError
            raise PayPalError("GET order -> 404 RESOURCE_NOT_FOUND", status_code=404, debug_id="d")
        if order_id in self.captures:
            return {"id": order_id, "status": "COMPLETED",
                    "payer": {"email_address": "buyer@example.com", "payer_id": "P1"},
                    "purchase_units": [{"custom_id": kw["custom_id"], "payments": {"captures": [
                        {"id": f"CAP-{order_id}", "status": "COMPLETED",
                         "amount": {"currency_code": "USD", "value": kw["amount"]}}]}}]}
        return {"id": order_id, "status": "APPROVED",
                "purchase_units": [{"custom_id": kw["custom_id"]}]}


@pytest.fixture
def env(tmp_path):
    st = store_mod.LocalJSONStore(str(tmp_path))
    pp = FakePayPalWithOrders()
    shop_tools.configure(st, pp)
    yield st, pp
    shop_tools.configure(None, None)


def _live(st, item_id="it_1", price=45.0):
    it = store_mod.Item(id=item_id, created=time.time(), photo_paths=[], status="live",
                        curator={}, appraiser={}, copywriter={}, title="Framed print",
                        description="A print.", tags=[], price=price, floor=30.0)
    st.save_item(it)
    return it


async def test_get_paypal_order_reads_from_paypal(env):
    st, pp = env
    _live(st)
    order = await pp.create_order(amount="45.00", custom_id="it_1", description="x")
    res = shop_tools.get_paypal_order(order["id"])
    assert res["status"] == "APPROVED"
    assert res["custom_id"] == "it_1"
    assert "raw" not in res


def test_get_paypal_order_error_is_returned_not_raised(env):
    res = shop_tools.get_paypal_order("nope")
    assert "error" in res


async def test_book_sale_refuses_uncaptured_and_books_captured(env):
    st, pp = env
    _live(st)
    order = await pp.create_order(amount="45.00", custom_id="it_1", description="x")
    st_item = st.get_item("it_1")
    st_item.paypal_order_id = order["id"]
    st.save_item(st_item)
    res = shop_tools.book_sale(order["id"])
    assert "error" in res and "not captured" in res["error"]
    pp.captures.append(order["id"])  # buyer approved + captured
    res = shop_tools.book_sale(order["id"])
    assert res["status"] == "paid"
    assert res["paypal_capture_id"] == f"CAP-{order['id']}"
    assert res["already_booked"] is False
    res2 = shop_tools.book_sale(order["id"])
    assert res2["already_booked"] is True
    assert len(st.list_ledger()) == 1


async def test_add_tracking_tool(env):
    st, pp = env
    _live(st)
    from shelf import checkout
    await checkout.start_checkout(st, pp, "it_1", public_url="https://x.test")
    await checkout.complete_checkout(st, pp, "ORD1")
    res = shop_tools.add_tracking("it_1", "9400 1111", "usps")
    assert res["status"] == "shipped"
    assert res["tracking_number"] == "94001111"
    assert res["carrier"] == "USPS"
    assert shop_tools.add_tracking("it_1", "1", "USPS")["error"]  # already shipped


async def test_bookkeeper_tools(env):
    st, pp = env
    _live(st)
    from shelf import checkout
    await checkout.start_checkout(st, pp, "it_1", public_url="https://x.test")
    await checkout.complete_checkout(st, pp, "ORD1")
    led = shop_tools.ledger_summary()
    assert led["totals"]["paid_total"] == 45.0
    assert led["paid"][0]["paypal_capture_id"] == "CAP-ORD1"
    caps = shop_tools.list_paypal_captures()
    assert caps["captures"] == [{"item_id": "it_1", "order_id": "ORD1", "capture_id": "CAP-ORD1",
                                 "status": "COMPLETED", "amount": "45.00"}]
    assert caps["errors"] == []


def test_agents_module_builds_crew_and_desk():
    from shelf import agents
    assert [a.name for a in agents.item_crew.sub_agents] == ["curator", "appraiser", "copywriter"]
    assert agents.shopkeeper.name == "shopkeeper"
    assert agents.bookkeeper.name == "bookkeeper"
    assert len(agents.shopkeeper.tools) == 3
    assert len(agents.bookkeeper.tools) == 2
