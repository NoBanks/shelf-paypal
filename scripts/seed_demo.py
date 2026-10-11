"""Seed the store with the seller's REAL inventory so a fresh deploy is never empty.

Usage: python -m scripts.seed_demo [--reset]
Loads demo_inventory/listings.json (genuine crew output for four real framed prints,
see demo_inventory/README.md) and the matching photos. Items go live at the SELLER's
price; the appraiser's suggestion is kept on the item so the dashboard can show both.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import time

from shelf.store import Item, LocalJSONStore

INV = pathlib.Path("demo_inventory")
UPLOADS = pathlib.Path("data/uploads")


def seed(reset: bool = False) -> list[str]:
    if reset and pathlib.Path("data").exists():
        shutil.rmtree("data")
    store = LocalJSONStore("data")
    listings = json.loads((INV / "listings.json").read_text(encoding="utf-8"))
    made = []
    for i, rec in enumerate(listings):
        if store.get_item(rec["id"]) is not None and not reset:
            continue
        dest = UPLOADS / rec["id"]
        dest.mkdir(parents=True, exist_ok=True)
        paths = []
        for n, name in enumerate(rec["photos"]):  # already in hero-first order
            target = dest / f"photo_{n}.jpg"
            shutil.copyfile(INV / name, target)
            paths.append(str(target))
        appraiser = dict(rec.get("appraiser") or {})
        item = Item(
            id=rec["id"], created=time.time() - i, photo_paths=paths, status="live",
            curator=rec.get("curator") or {}, appraiser=appraiser, copywriter={},
            title=rec["title"], description=rec["description"], tags=rec.get("tags") or [],
            price=float(rec["price"]), floor=float(appraiser.get("suggested_floor") or 0) if str(appraiser.get("suggested_floor") or "").replace(".", "", 1).isdigit() else 0.0,
            seller_notes=rec.get("seller_notes", ""), seller_price=float(rec.get("seller_price") or rec["price"]),
        )
        store.save_item(item)
        made.append(rec["id"])
    return made


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="wipe data/ first")
    args = ap.parse_args()
    ids = seed(reset=args.reset)
    print(f"seeded {len(ids)} items: {', '.join(ids) or '(none, already present)'}")
