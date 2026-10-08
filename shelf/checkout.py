"""Deterministic checkout glue: item -> PayPal order -> capture -> ledger -> shipped.

No LLM anywhere in this module. Amounts come from the approved item record.
Every transition is idempotent on the PayPal capture id so a replayed webhook
or a double onApprove never double-books a sale.

Item status flow: draft -> live -> paid -> shipped
(the old manual "sold" state is still accepted for legacy items)
"""
from __future__ import annotations

import secrets
import time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol

from shelf.store import BaseStore, Item, LedgerEntry


class PayPalLike(Protocol):
    async def create_order(self, **kw: Any) -> dict: ...
    async def get_order(self, order_id: str) -> dict: ...
    async def capture_order(self, order_id: str) -> dict: ...
    async def add_tracking(self, order_id: str, *, capture_id: str, tracking_number: str,
                           carrier: str = "USPS", notify_payer: bool = True) -> dict: ...


def money(value: float | int | str) -> str:
    """Format a price as PayPal wants it: two decimals, half-up, no thousands separators."""
    d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{d:.2f}"


def _entry(item: Item, kind: str, amount: float, memo: str, capture_id: str = "") -> LedgerEntry:
    return LedgerEntry(id="le_" + secrets.token_hex(5), item_id=item.id, created=time.time(),
                       kind=kind, amount=float(amount), memo=memo, paypal_capture_id=capture_id)


async def start_checkout(store: BaseStore, paypal: PayPalLike, item_id: str, *, public_url: str,
                         brand_name: str = "SHELF") -> dict:
    """Create the PayPal order for a live item. Returns {order_id, approve_url}."""
    item = store.get_item(item_id)
    if item is None:
        raise KeyError(f"item not found: {item_id}")
    if item.status != "live":
        raise ValueError(f"item {item_id} is not for sale (status {item.status!r})")
    if not item.price or item.price <= 0:
        raise ValueError(f"item {item_id} has no price")
    amount = money(item.price)
    title = (item.title or "SHELF item")[:127]
    base = public_url.rstrip("/")
    order = await paypal.create_order(
        amount=amount,
        description=f"{title} (SHELF {item.id})",
        custom_id=item.id,
        items=[{"name": title, "unit_amount": amount, "quantity": 1, "sku": item.id}],
        return_url=f"{base}/store/{item.id}?paid=1",
        cancel_url=f"{base}/store/{item.id}",
        brand_name=brand_name,
    )
    item.paypal_order_id = order["id"]
    store.save_item(item)
    return {"order_id": order["id"], "approve_url": order.get("approve_url", ""), "status": order.get("status", "")}


def _find_by_order(store: BaseStore, order_id: str) -> Item | None:
    for it in store.list_items():
        if it.paypal_order_id == order_id:
            return it
    return None


def record_capture(store: BaseStore, summary: dict) -> Item | None:
    """Book a completed capture against its item. Idempotent. Returns the item or None if unknown."""
    item = None
    if summary.get("custom_id"):
        item = store.get_item(summary["custom_id"])
    if item is None and summary.get("order_id"):
        item = _find_by_order(store, summary["order_id"])
    if item is None:
        return None
    cap_id = summary.get("capture_id", "")
    if cap_id and item.paypal_capture_id == cap_id:
        return item  # replay
    if summary.get("capture_status", summary.get("status")) != "COMPLETED":
        return item  # pending / declined: nothing to book
    amount = float(summary.get("amount") or item.price or 0.0)
    item.status = "paid"
    item.sold_price = amount
    item.paypal_order_id = summary.get("order_id", "") or item.paypal_order_id
    item.paypal_capture_id = cap_id
    item.buyer_email = summary.get("payer_email", "")
    try:
        item.net_amount = float(summary.get("net_amount") or 0.0)
    except ValueError:
        item.net_amount = 0.0
    item.paid_at = time.time()
    store.save_item(item)
    store.add_ledger(_entry(item, "paid", amount, f"{item.title} via PayPal", cap_id))
    return item


async def complete_checkout(store: BaseStore, paypal: PayPalLike, order_id: str) -> Item:
    """Capture an approved order and book it. Idempotent on capture id."""
    existing = _find_by_order(store, order_id)
    if existing is not None and existing.paypal_capture_id:
        return existing  # already captured (webhook or earlier callback won the race)
    summary = await paypal.capture_order(order_id)  # raises PayPalError on decline
    item = record_capture(store, summary)
    if item is None:
        raise KeyError(f"captured order {order_id} does not match any item")
    return item


async def ship_item(store: BaseStore, paypal: PayPalLike, item_id: str, *, tracking_number: str,
                    carrier: str = "USPS") -> Item:
    """Post shipment tracking to PayPal (buyer gets notified) and mark the item shipped."""
    item = store.get_item(item_id)
    if item is None:
        raise KeyError(f"item not found: {item_id}")
    if item.status != "paid":
        raise ValueError(f"item {item_id} is not paid (status {item.status!r})")
    number = "".join(ch for ch in tracking_number if not ch.isspace())
    if not number:
        raise ValueError("tracking number required")
    await paypal.add_tracking(item.paypal_order_id, capture_id=item.paypal_capture_id,
                              tracking_number=number, carrier=carrier.upper())
    item.status = "shipped"
    item.tracking_number = number
    item.carrier = carrier.upper()
    item.shipped_at = time.time()
    store.save_item(item)
    store.add_ledger(_entry(item, "shipped", 0.0, f"{item.title} {carrier.upper()} {number}", item.paypal_capture_id))
    return item
