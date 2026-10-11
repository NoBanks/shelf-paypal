"""Run the real crew on the seller's real items and save the results as the demo inventory.

Usage: python -m scripts.build_inventory
Reads demo_inventory/items.json (photos + seller notes + seller price), runs the ADK crew
on each item with the seller notes, and writes demo_inventory/listings.json. The seed
script then loads those listings, so a fresh deploy shows genuine crew output, not mockups.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import tempfile

from shelf import publish
from shelf.run_local import load_key, rotate_key, run_item

INV = pathlib.Path("demo_inventory")


async def main() -> None:
    import sys
    items = json.loads((INV / "items.json").read_text(encoding="utf-8"))
    only = set(sys.argv[1:])
    prev = {}
    if only and (INV / "listings.json").exists():
        prev = {r["id"]: r for r in json.loads((INV / "listings.json").read_text(encoding="utf-8"))}
    out = []
    load_key()
    for it in items:
        if only and it["id"] not in only:
            out.append(prev[it["id"]]); continue
        photos = [INV / p for p in it["photos"]]
        for attempt in range(6):
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    crew = await run_item(photos, pathlib.Path(tmp), it["notes"])
                break
            except Exception as exc:
                print("  retry:", str(exc)[:80])
                rotate_key()
                await asyncio.sleep(5)
        built = publish.build_item_from_crew(it["id"], [str(p) for p in photos], crew,
                                             seller_notes=it["notes"], seller_price=it["price"])
        rec = {
            "id": it["id"], "photos": [pathlib.Path(p).name for p in built.photo_paths],
            "title": built.title, "description": built.description, "tags": built.tags,
            "suggested_price": built.price, "price": it["price"],
            "curator": built.curator, "appraiser": built.appraiser,
            "seller_notes": it["notes"], "seller_price": it["price"],
        }
        out.append(rec)
        print(f"{it['id']}: {built.title} | AI suggested {built.price} | seller {it['price']} | hero {rec['photos'][0]}")
    (INV / "listings.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", INV / "listings.json")


if __name__ == "__main__":
    asyncio.run(main())
