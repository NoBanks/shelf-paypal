"""Tools for the SHOPKEEPER and BOOKKEEPER agents.

Plain functions (ADK wraps them as function tools from the signature and
docstring). Every tool is thin glue over shelf.checkout and shelf.paypal, so
the agent can only do what the deterministic money path already allows.
The store and PayPal client are resolved lazily from the environment, or can
be injected for tests with `configure(store, paypal)`.
"""
from __future__ import annotations

import asyncio
from typing import Any

from shelf import checkout
from shelf.paypal import PayPalClient
from shelf.store import BaseStore, get_store

_store: BaseStore | None = None
_paypal: Any = None


def configure(store: BaseStore | None = None, paypal: Any = None) -> None:
    """Inject a store and a PayPal client (tests, or the web app at startup)."""
    global _store, _paypal
    _store = store
    _paypal = paypal


def _s() -> BaseStore:
    global _store
    if _store is None:
        _store = get_store()
    return _store


def _pp() -> Any:
    global _paypal
    if _paypal is None:
        _paypal = PayPalClient.from_env()
    if _paypal is None:
        raise RuntimeError("PayPal is not configured (PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET)")
    return _paypal


def _run(coro):
    """Run a coroutine from a sync tool, whether or not a loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, coro).result()


def get_paypal_order(order_id: str) -> dict:
    """Read a PayPal order straight from PayPal: status, capture id, amount, buyer email.

    Args:
        order_id: the PayPal order id (starts the checkout; stored on the item as paypal_order_id).

    Returns:
        {order_id, status, capture_id, capture_status, amount, currency, payer_email} from PayPal,
        or {error} if PayPal rejected the request.
    """
    from shelf.paypal import PayPalError, summarize_capture
    try:
        raw = _run(_pp().get_order(order_id))
    except PayPalError as exc:
        return {"error": str(exc), "debug_id": exc.debug_id}
    s = summarize_capture(raw)
    s.pop("raw", None)
    return s


def book_sale(order_id: str) -> dict:
    """Book a COMPLETED PayPal order into the SHELF ledger (idempotent) and mark the item paid.

    Args:
        order_id: the PayPal order id.

    Returns:
        {item_id, status, sold_price, paypal_capture_id, already_booked} or {error}.
    """
    from shelf.paypal import PayPalError, summarize_capture
    store = _s()
    try:
        raw = _run(_pp().get_order(order_id))
    except PayPalError as exc:
        return {"error": str(exc), "debug_id": exc.debug_id}
    summary = summarize_capture(raw)
    if summary.get("capture_status") != "COMPLETED":
        return {"error": f"order {order_id} is not captured (status {summary.get('status') or 'unknown'})"}
    before = checkout._find_by_order(store, order_id)
    already = bool(before and before.paypal_capture_id)
    item = checkout.record_capture(store, summary)
    if item is None:
        return {"error": f"order {order_id} does not match any SHELF item"}
    return {"item_id": item.id, "status": item.status, "sold_price": item.sold_price,
            "paypal_capture_id": item.paypal_capture_id, "already_booked": already}


def add_tracking(item_id: str, tracking_number: str, carrier: str = "USPS") -> dict:
    """Post shipment tracking to PayPal for a paid item so the buyer is notified; marks it shipped.

    Args:
        item_id: the SHELF item id (it_...).
        tracking_number: carrier tracking number as printed on the label.
        carrier: USPS, UPS, FEDEX, DHL or OTHER.

    Returns:
        {item_id, status, tracking_number, carrier} or {error}.
    """
    from shelf.paypal import PayPalError
    try:
        item = _run(checkout.ship_item(_s(), _pp(), item_id, tracking_number=tracking_number, carrier=carrier))
    except (KeyError, ValueError, PayPalError) as exc:
        return {"error": str(exc)}
    return {"item_id": item.id, "status": item.status, "tracking_number": item.tracking_number,
            "carrier": item.carrier}


def ledger_summary() -> dict:
    """Read the SHELF ledger totals and the paid entries with their PayPal capture ids.

    Returns:
        {totals: {...}, paid: [{item_id, amount, paypal_capture_id, memo}]}.
    """
    store = _s()
    paid = [{"item_id": e.item_id, "amount": e.amount, "paypal_capture_id": e.paypal_capture_id, "memo": e.memo}
            for e in store.list_ledger() if e.kind == "paid"]
    return {"totals": store.totals(), "paid": paid}


def list_paypal_captures() -> dict:
    """List captures PayPal knows about for this seller's items (by reading each item's PayPal order).

    Returns:
        {captures: [{item_id, order_id, capture_id, status, amount}], errors: [...]}.
    """
    from shelf.paypal import PayPalError, summarize_capture
    store = _s()
    out: list[dict] = []
    errors: list[str] = []
    for it in store.list_items():
        if not it.paypal_order_id:
            continue
        try:
            raw = _run(_pp().get_order(it.paypal_order_id))
        except PayPalError as exc:
            errors.append(f"{it.id}: {exc}")
            continue
        s = summarize_capture(raw)
        out.append({"item_id": it.id, "order_id": it.paypal_order_id, "capture_id": s["capture_id"],
                    "status": s["capture_status"] or s["status"], "amount": s["amount"]})
    return {"captures": out, "errors": errors}
