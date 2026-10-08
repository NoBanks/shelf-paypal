"""PayPal Orders v2 client for SHELF (sandbox by default).

Small, typed, no SDK: httpx against https://api-m.sandbox.paypal.com.
Covers exactly what the storefront needs: OAuth client-credentials token,
create order (intent CAPTURE), get order, capture, add shipment tracking.

Money-path law (same as the NoBanks listing engine): no model is ever in this
file. Agents call these functions through tools; the amounts come from the
approved item record, never from an LLM.
"""
from __future__ import annotations

import base64
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

SANDBOX_URL = "https://api-m.sandbox.paypal.com"
PRODUCTION_URL = "https://api-m.paypal.com"


class PayPalError(Exception):
    """A non-2xx reply from PayPal, with the fields a human needs to debug it."""

    def __init__(self, message: str, status_code: int = 0, debug_id: str = "", body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.debug_id = debug_id
        self.body = body


@dataclass
class PayPalClient:
    client_id: str
    secret: str
    base_url: str = SANDBOX_URL
    currency: str = "USD"
    timeout: float = 30.0
    _token: str = field(default="", repr=False)
    _token_expires_at: float = field(default=0.0, repr=False)

    # ----- construction -----
    @classmethod
    def from_env(cls) -> "PayPalClient | None":
        """Build from PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET; None when unset."""
        cid = os.environ.get("PAYPAL_CLIENT_ID", "").strip()
        sec = os.environ.get("PAYPAL_CLIENT_SECRET", "").strip()
        if not cid or not sec:
            return None
        env = os.environ.get("PAYPAL_ENVIRONMENT", "SANDBOX").strip().upper()
        base = PRODUCTION_URL if env == "PRODUCTION" else SANDBOX_URL
        return cls(client_id=cid, secret=sec, base_url=base,
                   currency=os.environ.get("PAYPAL_CURRENCY", "USD"))

    @property
    def is_sandbox(self) -> bool:
        return self.base_url == SANDBOX_URL

    # ----- auth -----
    async def access_token(self, force: bool = False) -> str:
        if self._token and not force and time.time() < self._token_expires_at - 60:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.secret}".encode()).decode()
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            resp = await http.post(
                f"{self.base_url}/v1/oauth2/token",
                headers={"Authorization": f"Basic {basic}",
                         "Content-Type": "application/x-www-form-urlencoded"},
                content=b"grant_type=client_credentials",
            )
        if resp.status_code != 200:
            raise PayPalError(f"token request failed: {resp.status_code} {resp.text[:200]}",
                              status_code=resp.status_code, body=_safe_json(resp))
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + float(data.get("expires_in", 3600))
        return self._token

    async def _request(self, method: str, path: str, json: Any = None,
                       extra_headers: dict[str, str] | None = None) -> Any:
        """Authenticated request; refreshes the token once on 401."""
        for attempt in (0, 1):
            tok = await self.access_token(force=attempt == 1)
            headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
                       "Prefer": "return=representation"}
            if extra_headers:
                headers.update(extra_headers)
            async with httpx.AsyncClient(timeout=self.timeout) as http:
                resp = await http.request(method, f"{self.base_url}{path}", json=json, headers=headers)
            if resp.status_code == 401 and attempt == 0:
                continue
            if resp.status_code >= 300:
                body = _safe_json(resp)
                issue = ""
                if isinstance(body, dict):
                    details = body.get("details") or []
                    if details and isinstance(details[0], dict):
                        issue = details[0].get("issue", "")
                    name = body.get("name", "")
                    debug_id = body.get("debug_id", "")
                else:
                    name, debug_id = "", ""
                raise PayPalError(
                    f"{method} {path} -> {resp.status_code} {name} {issue}".strip(),
                    status_code=resp.status_code, debug_id=debug_id, body=body)
            return _safe_json(resp)
        raise PayPalError("unreachable")  # pragma: no cover

    # ----- orders -----
    async def create_order(self, *, amount: str, description: str, custom_id: str,
                           items: list[dict] | None = None, return_url: str = "",
                           cancel_url: str = "", brand_name: str = "SHELF",
                           shipping_preference: str = "GET_FROM_FILE") -> dict:
        """POST /v2/checkout/orders with intent CAPTURE. Returns {id, status, approve_url, raw}."""
        cur = self.currency
        unit: dict[str, Any] = {
            "reference_id": custom_id,
            "custom_id": custom_id,
            "description": description[:127],
            "amount": {"currency_code": cur, "value": amount,
                       "breakdown": {"item_total": {"currency_code": cur, "value": amount}}},
        }
        if items:
            unit["items"] = [
                {"name": it["name"][:127], "quantity": str(it.get("quantity", 1)),
                 "sku": str(it.get("sku", custom_id))[:127],
                 "category": it.get("category", "PHYSICAL_GOODS"),
                 "unit_amount": {"currency_code": cur, "value": it["unit_amount"]}}
                for it in items
            ]
        ctx: dict[str, Any] = {"brand_name": brand_name, "user_action": "PAY_NOW",
                               "shipping_preference": shipping_preference,
                               "landing_page": "NO_PREFERENCE",
                               "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED"}
        if return_url:
            ctx["return_url"] = return_url
        if cancel_url:
            ctx["cancel_url"] = cancel_url
        payload = {"intent": "CAPTURE", "purchase_units": [unit],
                   "payment_source": {"paypal": {"experience_context": ctx}}}
        raw = await self._request("POST", "/v2/checkout/orders", json=payload,
                                  extra_headers={"PayPal-Request-Id": f"shelf-{custom_id}-{uuid.uuid4().hex[:12]}"})
        return {"id": raw["id"], "status": raw.get("status", ""),
                "approve_url": _link(raw, "payer-action") or _link(raw, "approve"), "raw": raw}

    async def get_order(self, order_id: str) -> dict:
        return await self._request("GET", f"/v2/checkout/orders/{order_id}")

    async def capture_order(self, order_id: str) -> dict:
        """POST capture. Returns a flat summary a ledger can store."""
        raw = await self._request("POST", f"/v2/checkout/orders/{order_id}/capture", json={},
                                  extra_headers={"PayPal-Request-Id": f"shelf-cap-{order_id}"})
        return summarize_capture(raw)

    async def add_tracking(self, order_id: str, *, capture_id: str, tracking_number: str,
                           carrier: str = "USPS", notify_payer: bool = True) -> dict:
        raw = await self._request("POST", f"/v2/checkout/orders/{order_id}/track",
                                  json={"capture_id": capture_id, "tracking_number": tracking_number,
                                        "carrier": carrier, "notify_payer": notify_payer})
        tracker_id = ""
        try:
            tracker_id = raw["purchase_units"][0]["shipping"]["trackers"][0]["id"]
        except (KeyError, IndexError, TypeError):
            pass
        return {"order_id": order_id, "tracker_id": tracker_id, "raw": raw}


    # ----- webhooks -----
    async def verify_webhook(self, headers: dict, event: dict, *, webhook_id: str) -> bool:
        """POST /v1/notifications/verify-webhook-signature. True only on SUCCESS."""
        h = {k.lower(): v for k, v in headers.items()}
        payload = {
            "auth_algo": h.get("paypal-auth-algo", ""),
            "cert_url": h.get("paypal-cert-url", ""),
            "transmission_id": h.get("paypal-transmission-id", ""),
            "transmission_sig": h.get("paypal-transmission-sig", ""),
            "transmission_time": h.get("paypal-transmission-time", ""),
            "webhook_id": webhook_id,
            "webhook_event": event,
        }
        try:
            res = await self._request("POST", "/v1/notifications/verify-webhook-signature", json=payload)
        except PayPalError:
            return False
        return isinstance(res, dict) and res.get("verification_status") == "SUCCESS"


def summarize_capture(raw: dict) -> dict:
    """Flatten a capture (or webhook resource) response to what the ledger needs."""
    units = raw.get("purchase_units") or [{}]
    unit = units[0] if units else {}
    captures = ((unit.get("payments") or {}).get("captures")) or [{}]
    cap = captures[0] if captures else {}
    amount = (cap.get("amount") or {}).get("value", "")
    net = ((cap.get("seller_receivable_breakdown") or {}).get("net_amount") or {}).get("value", "")
    payer = raw.get("payer") or {}
    return {
        "order_id": raw.get("id", ""),
        "status": raw.get("status", ""),
        "capture_id": cap.get("id", ""),
        "capture_status": cap.get("status", ""),
        "amount": amount,
        "net_amount": net,
        "currency": (cap.get("amount") or {}).get("currency_code", ""),
        "custom_id": unit.get("custom_id", "") or cap.get("custom_id", ""),
        "payer_email": payer.get("email_address", ""),
        "payer_id": payer.get("payer_id", ""),
        "raw": raw,
    }


def summarize_webhook_capture(resource: dict) -> dict:
    """Flatten a PAYMENT.CAPTURE.COMPLETED webhook resource to the ledger shape."""
    related = ((resource.get("supplementary_data") or {}).get("related_ids")) or {}
    return {
        "order_id": related.get("order_id", ""),
        "status": resource.get("status", ""),
        "capture_id": resource.get("id", ""),
        "capture_status": resource.get("status", ""),
        "amount": (resource.get("amount") or {}).get("value", ""),
        "net_amount": ((resource.get("seller_receivable_breakdown") or {}).get("net_amount") or {}).get("value", ""),
        "currency": (resource.get("amount") or {}).get("currency_code", ""),
        "custom_id": resource.get("custom_id", ""),
        "payer_email": "",
        "payer_id": "",
        "raw": resource,
    }


def _link(raw: dict, rel: str) -> str:
    for ln in raw.get("links") or []:
        if ln.get("rel") == rel:
            return ln.get("href", "")
    return ""


def _safe_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return {"text": resp.text[:500]}
