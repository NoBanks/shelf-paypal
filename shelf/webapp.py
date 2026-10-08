"""SHELF web app: upload photos, watch the crew work live, approve, sell.

Run: uvicorn shelf.webapp:app --port 8080
The one file NIM was not trusted with; hand-written against the M2 PRD.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import secrets
import time

from fastapi import FastAPI, HTTPException, Request
# isinstance check must target starlette's UploadFile: request.form() yields
# starlette instances, and fastapi.UploadFile is a SUBCLASS - checking against
# the fastapi class matches nothing and every upload 400s (found 2026-08-17
# feeding the first real items through the live site).
from starlette.datastructures import UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from shelf import publish, ui
from shelf.store import Item, get_store

UPLOADS = pathlib.Path("data/uploads")


def create_app() -> FastAPI:
    app = FastAPI(title="SHELF")
    store = get_store()
    events: dict[str, list[dict]] = {}

    def push(item_id: str, agent: str, text: str) -> None:
        events.setdefault(item_id, []).append(
            {"ts": time.time(), "agent": agent, "text": text}
        )

    async def crew_task(item_id: str, photos: list[pathlib.Path]) -> None:
        push(item_id, "crew", "started")
        try:
            from shelf.run_local import load_key, rotate_key, run_item

            rotate_key()  # PROACTIVE per-item rotation: fresh key per item (43x20/day pool math)
            # Quota-rotation retry (2026-08-19): a starved key must never kill
            # an item. Rotate through the pool on 429/503-class errors.
            QUOTA_MARKERS = ("429", "resource_exhausted", "quota", "503",
                             "unavailable", "overloaded", "rate limit")
            out = None
            last_exc: Exception | None = None
            for attempt in range(10):
                try:
                    out = await run_item(photos, UPLOADS / item_id)
                    break
                except Exception as exc:
                    if any(m in str(exc).lower() for m in QUOTA_MARKERS):
                        rotate_key()
                        push(item_id, "crew",
                             f"quota hit, rotated key (attempt {attempt + 1})")
                        last_exc = exc
                        await asyncio.sleep(30)  # let per-minute rate windows clear before retrying on the fresh key
                        continue
                    raise
            if out is None:
                raise last_exc if last_exc else RuntimeError("crew failed")
            for agent in ("curator", "appraiser", "copywriter"):
                if agent in out:
                    push(item_id, agent, out[agent][:200])
            item = publish.build_item_from_crew(
                item_id, [str(p) for p in photos], out
            )
            store.save_item(item)
            push(item_id, "crew", "draft ready")
        except Exception as exc:  # surface, never hide
            existing = store.get_item(item_id)
            if existing:
                existing.status = "draft"
                existing.notes = f"error: {exc}"
                store.save_item(existing)
            push(item_id, "crew", f"error: {exc}")

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> str:
        return ui.DASHBOARD_HTML

    @app.get("/store", response_class=HTMLResponse)
    async def storefront() -> str:
        return ui.STORE_HTML

    @app.get("/ledger", response_class=HTMLResponse)
    async def ledger_page() -> str:
        return ui.LEDGER_HTML

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True}

    @app.post("/api/items")
    async def create_item(request: Request) -> dict:
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
            try:  # durable copy - survives instance restarts
                from google.cloud import storage as gcs
                gcs.Client().bucket("shelf-agentic-nbn-uploads").blob(
                    f"{item_id}/{dest.name}").upload_from_filename(str(dest))
            except Exception:
                pass  # local copy still serves this instance's lifetime
        item = Item(
            id=item_id,
            created=time.time(),
            photo_paths=[str(p) for p in photos],
            status="processing",
            curator={},
            appraiser={},
            copywriter={},
        )
        store.save_item(item)
        asyncio.create_task(crew_task(item_id, photos))
        return {"item_id": item_id}

    def _thumb(item: Item) -> str:
        if not item.photo_paths:
            return ""
        p = pathlib.Path(item.photo_paths[0])
        return f"/uploads/{item.id}/{p.name}"

    @app.get("/api/items")
    async def list_items() -> list[dict]:
        return [
            {
                "id": it.id,
                "status": it.status,
                "title": it.title or "(processing)",
                "price": it.price,
                "description": it.description,
                "thumb": _thumb(it),
                # renderCard() builds card thumbnails from photo_paths; omitting it
                # starved the dashboard of images entirely (found filming the demo 8/20)
                "photo_paths": it.photo_paths,
                "notes": it.notes,
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
    async def approve(item_id: str) -> dict:
        item = publish.approve(store, item_id)
        return {"status": item.status}

    @app.post("/api/items/{item_id}/sold")
    async def sold(item_id: str, request: Request) -> dict:
        body = await request.json()
        item = publish.mark_sold(store, item_id, float(body["price"]))
        return {"status": item.status}

    @app.post("/api/items/{item_id}/paid")
    async def paid(item_id: str) -> dict:
        item = publish.mark_paid(store, item_id)
        return {"status": item.status}

    @app.get("/api/store-items")
    async def store_items() -> list[dict]:
        return [
            {
                "id": it.id,
                "title": it.title,
                "price": it.price,
                "description": it.description,
                "thumb": _thumb(it),
                "photos": [
                    f"/uploads/{it.id}/{pathlib.Path(p).name}"
                    for p in it.photo_paths
                ],
            }
            for it in store.list_items(status="live")
        ]

    @app.get("/api/ledger")
    async def ledger_api() -> dict:
        return {
            "totals": store.totals(),
            "entries": [
                {
                    "created": e.created,
                    "kind": e.kind,
                    "amount": e.amount,
                    "memo": e.memo,
                }
                for e in store.list_ledger()
            ],
        }

    @app.get("/uploads/{item_id}/{filename}")
    async def serve_upload(item_id: str, filename: str):
        # DURABLE IMAGES (2026-08-19): local disk is EPHEMERAL on Cloud Run -
        # every deploy/restart wiped all photos (store showed blank cards).
        # GCS bucket is the source of truth; local disk is just a warm cache.
        local = UPLOADS / item_id / filename
        if not local.exists():
            from fastapi.responses import RedirectResponse
            return RedirectResponse(
                f"https://storage.googleapis.com/shelf-agentic-nbn-uploads/{item_id}/{filename}",
                status_code=307)
        return FileResponse(local)

    async def _old_serve_upload(item_id: str, filename: str) -> FileResponse:
        base = UPLOADS.resolve()
        path = (UPLOADS / item_id / filename).resolve()
        if not str(path).startswith(str(base)) or not path.exists():
            raise HTTPException(404)
        return FileResponse(path)

    return app


app = create_app()
