"""SHELF web app: upload photos, watch the crew work live, approve, sell through PayPal.

Run: uvicorn shelf.webapp:app --port 8080

Routes
  GET  /                      seller dashboard
  GET  /store                 public storefront (live items)
  GET  /store/{item_id}       item page with the PayPal button
  GET  /ledger                ledger
  POST /api/items             upload 1-6 photos, crew runs in the background
  POST /api/items/{id}/approve     (admin) draft -> live
  POST /api/items/{id}/ship        (admin) paid -> shipped, posts tracking to PayPal
  GET  /api/paypal/config          browser-safe client id + sandbox flag
  POST /api/paypal/orders          {item_id} -> PayPal order (Orders v2, intent CAPTURE)
  POST /api/paypal/orders/{id}/capture   capture after buyer approval, books the sale
  POST /api/paypal/webhook         PAYMENT.CAPTURE.COMPLETED as a second source of truth
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib
import secrets
import time
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Request
# isinstance check must target starlette's UploadFile: request.form() yields
# starlette instances, and fastapi.UploadFile is a SUBCLASS - checking against
# the fastapi class matches nothing and every upload 400s (found 2026-08-17
# feeding the first real items through the live site).
from starlette.datastructures import UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse

from shelf import checkout, desk, publish, shop_tools, ui
from shelf.paypal import PayPalClient, PayPalError, summarize_webhook_capture
from shelf.store import BaseStore, Item, get_store

UPLOADS = pathlib.Path("data/uploads")
GCS_BUCKET = os.environ.get("SHELF_GCS_BUCKET", "")


def _public_url(request: Request) -> str:
    env = os.environ.get("PUBLIC_URL", "").strip()
    if env:
        return env.rstrip("/")
    return str(request.base_url).rstrip("/")


def _require_admin(request: Request) -> None:
    """If SHELF_ADMIN_TOKEN is set, seller actions need it (header X-Shelf-Admin or ?token=)."""
    token = os.environ.get("SHELF_ADMIN_TOKEN", "").strip()
    if not token:
        return
    given = request.headers.get("x-shelf-admin") or request.query_params.get("token") or ""
    if not secrets.compare_digest(given, token):
        raise HTTPException(401, "admin token required")


def _item_public(it: Item) -> dict:
    return {
        "id": it.id,
        "title": it.title,
        "price": it.price,
        "description": it.description,
        "status": it.status,
        "thumb": _thumb(it),
        "photos": [f"/uploads/{it.id}/{pathlib.Path(p).name}" for p in it.photo_paths],
        "condition": (it.curator or {}).get("condition", ""),
        "flaws": (it.curator or {}).get("visible_flaws", []),
        "tags": it.tags,
    }


def _thumb(item: Item) -> str:
    if not item.photo_paths:
        return ""
    p = pathlib.Path(item.photo_paths[0])
    return f"/uploads/{item.id}/{p.name}"


def create_app(store: BaseStore | None = None, paypal: object | None = None) -> FastAPI:
    app = FastAPI(title="SHELF x PayPal")
    store = store or get_store()
    paypal = paypal if paypal is not None else PayPalClient.from_env()
    shop_tools.configure(store, paypal)  # agents share the app's store and PayPal client
    events: dict[str, list[dict]] = {}
    desk_notes: dict[str, str] = {}

    def push(item_id: str, agent: str, text: str) -> None:
        events.setdefault(item_id, []).append({"ts": time.time(), "agent": agent, "text": text})

    async def shopkeeper_task(item_id: str, tracking_number: str = "", carrier: str = "") -> None:
        """Post-sale agent pass. Runs after the capture is already booked; failures are logged only."""
        item = store.get_item(item_id)
        if item is None:
            return
        push(item_id, "shopkeeper", "on it: confirming with PayPal")
        try:
            note = await desk.run_shopkeeper(item, tracking_number, carrier)
            desk_notes[item_id] = note
            fresh = store.get_item(item_id)
            if fresh is not None and note and not note.startswith("shopkeeper skipped"):
                fresh.notes = note[:600]
                store.save_item(fresh)
            push(item_id, "shopkeeper", note[:300] if note else "done")
        except Exception as exc:  # never let an agent error touch the money path
            push(item_id, "shopkeeper", f"error: {exc}")

    def need_paypal():
        if paypal is None:
            raise HTTPException(503, "PayPal is not configured (set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)")
        return paypal

    async def crew_task(item_id: str, photos: list[pathlib.Path]) -> None:
        push(item_id, "crew", "started")
        try:
            from shelf.run_local import rotate_key, run_item

            rotate_key()  # fresh key per item
            QUOTA_MARKERS = ("429", "resource_exhausted", "quota", "503", "unavailable", "overloaded", "rate limit")
            out = None
            last_exc: Exception | None = None
            for attempt in range(10):
                try:
                    out = await run_item(photos, UPLOADS / item_id)
                    break
                except Exception as exc:
                    if any(m in str(exc).lower() for m in QUOTA_MARKERS):
                        rotate_key()
                        push(item_id, "crew", f"quota hit, rotated key (attempt {attempt + 1})")
                        last_exc = exc
                        await asyncio.sleep(30)
                        continue
                    raise
            if out is None:
                raise last_exc if last_exc else RuntimeError("crew failed")
            for agent in ("curator", "appraiser", "copywriter"):
                if agent in out:
                    push(item_id, agent, out[agent][:200])
            item = publish.build_item_from_crew(item_id, [str(p) for p in photos], out)
            store.save_item(item)
            push(item_id, "crew", "draft ready")
        except Exception as exc:  # surface, never hide
            existing = store.get_item(item_id)
            if existing:
                existing.status = "draft"
                existing.notes = f"error: {exc}"
                store.save_item(existing)
            push(item_id, "crew", f"error: {exc}")

    # ----- pages -----
    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> str:
        return ui.DASHBOARD_HTML

    @app.get("/store", response_class=HTMLResponse)
    async def storefront() -> str:
        return ui.STORE_HTML

    @app.get("/store/{item_id}", response_class=HTMLResponse)
    async def item_page(item_id: str) -> str:
        if store.get_item(item_id) is None:
            raise HTTPException(404)
        return ui.ITEM_HTML

    @app.get("/ledger", response_class=HTMLResponse)
    async def ledger_page() -> str:
        return ui.LEDGER_HTML

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True, "paypal": paypal is not None}

    # ----- items / crew -----
    @app.post("/api/items")
    async def create_item(request: Request) -> dict:
        _require_admin(request)
        form = await request.form()
        files = [v for v in form.values() if isinstance(v, UploadFile)]
        if not files or len(files) > 6:
            raise HTTPException(400, "upload 1 to 6 photos")
        item_id = "it_" + secrets.token_hex(5)
        item_dir = UPLOADS / item_id
        item_dir.mkdir(parents=True, exist_ok=True)
        photos: list[pathlib.Path] = []
        for i, f in enumerate(files):
            suffix = pathlib.Path(f.filename or "photo.jpg").suffix or ".jpg"
            dest = item_dir / f"photo_{i}{suffix}"
            dest.write_bytes(await f.read())
            photos.append(dest)
            if GCS_BUCKET:
                try:  # durable copy - survives instance restarts
                    from google.cloud import storage as gcs
                    gcs.Client().bucket(GCS_BUCKET).blob(f"{item_id}/{dest.name}").upload_from_filename(str(dest))
                except Exception:
                    pass
        item = Item(id=item_id, created=time.time(), photo_paths=[str(p) for p in photos],
                    status="processing", curator={}, appraiser={}, copywriter={})
        store.save_item(item)
        asyncio.create_task(crew_task(item_id, photos))
        return {"item_id": item_id}

    @app.get("/api/items")
    async def list_items() -> list[dict]:
        return [
            {
                "id": it.id, "status": it.status, "title": it.title or "(processing)",
                "price": it.price, "description": it.description, "thumb": _thumb(it),
                "photo_paths": it.photo_paths, "notes": it.notes,
                "paypal_order_id": it.paypal_order_id, "paypal_capture_id": it.paypal_capture_id,
                "buyer_email": it.buyer_email, "sold_price": it.sold_price, "net_amount": it.net_amount,
                "tracking_number": it.tracking_number, "carrier": it.carrier,
            }
            for it in store.list_items()
        ]

    @app.get("/api/items/{item_id}/events")
    async def item_events(item_id: str) -> StreamingResponse:
        async def stream():
            sent = 0
            for _ in range(600):  # up to 5 minutes
                buf = events.get(item_id, [])
                while sent < len(buf):
                    yield f"data: {json.dumps(buf[sent])}\n\n"
                    sent += 1
                item = store.get_item(item_id)
                if item and item.status != "processing" and sent >= len(buf):
                    yield 'data: {"agent": "crew", "text": "[done]"}\n\n'
                    return
                await asyncio.sleep(0.5)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/items/{item_id}/approve")
    async def approve(item_id: str, request: Request) -> dict:
        _require_admin(request)
        try:
            item = publish.approve(store, item_id)
        except KeyError:
            raise HTTPException(404)
        except ValueError as exc:
            raise HTTPException(409, str(exc))
        return {"status": item.status}

    @app.post("/api/items/{item_id}/ship")
    async def ship(item_id: str, request: Request) -> dict:
        _require_admin(request)
        body = await request.json()
        try:
            item = await checkout.ship_item(store, need_paypal(), item_id,
                                            tracking_number=str(body.get("tracking_number", "")),
                                            carrier=str(body.get("carrier", "USPS") or "USPS"))
        except KeyError:
            raise HTTPException(404)
        except ValueError as exc:
            raise HTTPException(409, str(exc))
        except PayPalError as exc:
            raise HTTPException(502, f"PayPal tracking failed: {exc} (debug_id {exc.debug_id})")
        if desk.shopkeeper_enabled():
            asyncio.create_task(shopkeeper_task(item.id, item.tracking_number, item.carrier))
        return {"status": item.status, "tracking_number": item.tracking_number, "carrier": item.carrier}

    # legacy manual flow kept for items sold off-platform (cash pickup)
    @app.post("/api/items/{item_id}/sold")
    async def sold(item_id: str, request: Request) -> dict:
        _require_admin(request)
        body = await request.json()
        item = publish.mark_sold(store, item_id, float(body["price"]))
        return {"status": item.status}

    @app.post("/api/items/{item_id}/paid")
    async def paid(item_id: str, request: Request) -> dict:
        _require_admin(request)
        item = publish.mark_paid(store, item_id)
        return {"status": item.status}

    # ----- storefront data -----
    @app.get("/api/store-items")
    async def store_items() -> list[dict]:
        return [_item_public(it) for it in store.list_items(status="live")]

    @app.get("/api/store-items/{item_id}")
    async def store_item(item_id: str) -> dict:
        it = store.get_item(item_id)
        if it is None or it.status in ("processing", "draft"):
            raise HTTPException(404)
        return _item_public(it)

    # ----- PayPal -----
    @app.get("/api/paypal/config")
    async def paypal_config() -> dict:
        cid = os.environ.get("PAYPAL_CLIENT_ID", "").strip()
        sandbox = os.environ.get("PAYPAL_ENVIRONMENT", "SANDBOX").strip().upper() != "PRODUCTION"
        return {"enabled": bool(cid) and paypal is not None, "client_id": cid, "sandbox": sandbox,
                "currency": os.environ.get("PAYPAL_CURRENCY", "USD")}

    @app.post("/api/paypal/orders")
    async def paypal_create_order(request: Request) -> dict:
        body = await request.json()
        item_id = str(body.get("item_id", ""))
        try:
            res = await checkout.start_checkout(store, need_paypal(), item_id, public_url=_public_url(request))
        except KeyError:
            raise HTTPException(404, "item not found")
        except ValueError as exc:
            raise HTTPException(409, str(exc))
        except PayPalError as exc:
            raise HTTPException(502, f"PayPal order failed: {exc} (debug_id {exc.debug_id})")
        return {"id": res["order_id"], "approve_url": res["approve_url"], "status": res["status"]}

    @app.post("/api/paypal/orders/{order_id}/capture")
    async def paypal_capture(order_id: str) -> dict:
        try:
            item = await checkout.complete_checkout(store, need_paypal(), order_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc))
        except PayPalError as exc:
            status = 402 if exc.status_code in (402, 422) else 502
            raise HTTPException(status, f"PayPal capture failed: {exc} (debug_id {exc.debug_id})")
        if desk.shopkeeper_enabled():
            asyncio.create_task(shopkeeper_task(item.id))
        return {"status": "COMPLETED", "order_id": order_id, "capture_id": item.paypal_capture_id,
                "amount": item.sold_price, "item": _item_public(item)}

    @app.post("/api/paypal/webhook")
    async def paypal_webhook(request: Request) -> dict:
        raw = await request.body()
        try:
            event = json.loads(raw or b"{}")
        except ValueError:
            raise HTTPException(400, "invalid json")
        webhook_id = os.environ.get("PAYPAL_WEBHOOK_ID", "").strip()
        if webhook_id and paypal is not None:
            ok = await paypal.verify_webhook(dict(request.headers), event, webhook_id=webhook_id)
            if not ok:
                raise HTTPException(400, "webhook signature verification failed")
        elif os.environ.get("SHELF_ALLOW_UNVERIFIED_WEBHOOKS") != "1":
            raise HTTPException(400, "webhook not verifiable: set PAYPAL_WEBHOOK_ID")
        if event.get("event_type") != "PAYMENT.CAPTURE.COMPLETED":
            return {"handled": False, "event_type": event.get("event_type", "")}
        summary = summarize_webhook_capture(event.get("resource") or {})
        item = checkout.record_capture(store, summary)
        if item is not None and desk.shopkeeper_enabled():
            asyncio.create_task(shopkeeper_task(item.id))
        return {"handled": item is not None, "item_id": item.id if item else None,
                "capture_id": summary["capture_id"]}

    # ----- desk (agents after the sale) -----
    @app.get("/api/items/{item_id}/desk")
    async def desk_note(item_id: str) -> dict:
        return {"item_id": item_id, "note": desk_notes.get(item_id, ""),
                "events": events.get(item_id, [])[-20:]}

    @app.post("/api/bookkeeper")
    async def bookkeeper_report(request: Request) -> dict:
        _require_admin(request)
        try:
            report = await desk.run_bookkeeper()
        except Exception as exc:
            raise HTTPException(502, f"bookkeeper failed: {exc}")
        return {"report": report, "totals": store.totals()}

    # ----- ledger -----
    @app.get("/api/ledger")
    async def ledger_api() -> dict:
        return {
            "totals": store.totals(),
            "entries": [
                {"created": e.created, "kind": e.kind, "amount": e.amount, "memo": e.memo,
                 "item_id": e.item_id, "paypal_capture_id": e.paypal_capture_id}
                for e in store.list_ledger()
            ],
        }

    @app.get("/uploads/{item_id}/{filename}")
    async def serve_upload(item_id: str, filename: str):
        base = UPLOADS.resolve()
        local = (UPLOADS / item_id / filename).resolve()
        if not str(local).startswith(str(base)):
            raise HTTPException(404)
        if not local.exists():
            if GCS_BUCKET:
                return RedirectResponse(f"https://storage.googleapis.com/{GCS_BUCKET}/{item_id}/{filename}",
                                        status_code=307)
            raise HTTPException(404)
        return FileResponse(local)

    return app


app = create_app()
