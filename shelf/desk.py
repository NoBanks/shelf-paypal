"""Run the SHOPKEEPER and BOOKKEEPER agents (ADK) on demand.

These run AFTER money has moved. They never gate a capture: if Gemini is
unavailable the sale is still booked by shelf.checkout and the agent simply
reports that it could not run.
"""
from __future__ import annotations

import os

from shelf.store import Item


def gemini_available() -> bool:
    from shelf.run_local import _pool
    return bool(_pool())


async def _run_agent(agent, prompt: str, user_id: str = "seller") -> str:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from shelf.run_local import load_key

    load_key()
    runner = InMemoryRunner(agent=agent, app_name="shelf-desk")
    session = await runner.session_service.create_session(app_name="shelf-desk", user_id=user_id)
    msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    out: list[str] = []
    async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=msg):
        if event.content and event.content.parts:
            text = "".join(pt.text or "" for pt in event.content.parts)
            if text.strip():
                out.append(text)
    return "\n".join(out).strip()


async def run_shopkeeper(item: Item, tracking_number: str = "", carrier: str = "") -> str:
    """Post-sale pass for one item. Returns the agent's plain-text buyer note."""
    if not gemini_available():
        return "shopkeeper skipped: no Gemini key configured"
    from shelf.agents import shopkeeper

    prompt = (
        f"A buyer paid for SHELF item {item.id} ('{item.title}') through PayPal. "
        f"PayPal order id: {item.paypal_order_id}. "
        + (f"The seller shipped it: tracking {tracking_number} via {carrier}. " if tracking_number else "")
        + "Confirm the order with PayPal, book it, "
        + ("post the tracking, " if tracking_number else "")
        + "then write the buyer note."
    )
    return await _run_agent(shopkeeper, prompt)


async def run_bookkeeper() -> str:
    """Ledger vs PayPal reconciliation report, plain text."""
    if not gemini_available():
        return "bookkeeper skipped: no Gemini key configured"
    from shelf.agents import bookkeeper

    return await _run_agent(bookkeeper, "Reconcile the SHELF ledger against PayPal and report.")


def shopkeeper_enabled() -> bool:
    return os.environ.get("SHELF_SHOPKEEPER", "1") != "0" and gemini_available()
