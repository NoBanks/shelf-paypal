"""Live sandbox smoke: token -> create order -> read it back. Needs ~/.paypal/sandbox.env or env vars.

Usage: python -m scripts.live_smoke [--capture ORDER_ID]
Create needs no buyer. Capture only works after a sandbox buyer approved the order (open the
approve_url printed below, log in as the sandbox PERSONAL account, pay), then rerun with --capture.
"""
import argparse
import asyncio
import os
import pathlib

from shelf.paypal import PayPalClient, PayPalError


def load_env() -> None:
    p = pathlib.Path.home() / ".paypal" / "sandbox.env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


async def main(capture: str | None) -> None:
    load_env()
    pp = PayPalClient.from_env()
    if pp is None:
        raise SystemExit("no credentials: set PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET")
    print("base:", pp.base_url, "client id ends", pp.client_id[-6:])
    tok = await pp.access_token()
    print("token OK, length", len(tok))
    if capture:
        res = await pp.capture_order(capture)
        print("CAPTURE:", {k: v for k, v in res.items() if k != "raw"})
        return
    order = await pp.create_order(amount="45.00", description="SHELF live smoke: framed print",
                                  custom_id="it_demo_print",
                                  items=[{"name": "Framed abstract print", "unit_amount": "45.00",
                                          "quantity": 1, "sku": "it_demo_print"}],
                                  return_url="http://127.0.0.1:8080/store/it_demo_print?paid=1",
                                  cancel_url="http://127.0.0.1:8080/store/it_demo_print", brand_name="SHELF")
    print("ORDER:", order["id"], order["status"])
    print("APPROVE URL:", order["approve_url"])
    back = await pp.get_order(order["id"])
    print("GET ORDER status:", back.get("status"), "| intent:", back.get("intent"),
          "| amount:", back["purchase_units"][0]["amount"]["value"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", default=None)
    a = ap.parse_args()
    try:
        asyncio.run(main(a.capture))
    except PayPalError as exc:
        raise SystemExit(f"PAYPAL ERROR {exc.status_code} {exc} debug_id={exc.debug_id} body={exc.body}")
