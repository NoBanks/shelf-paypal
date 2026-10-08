"""Seed the local store with a few LIVE demo items so a fresh deploy is never empty.

Usage: python -m scripts.seed_demo [--reset]
Writes to data/ (the LocalJSONStore). Images are generated placeholders; replace
with real photos through the dashboard for the demo film.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import struct
import time
import zlib

from shelf.store import Item, LocalJSONStore

UPLOADS = pathlib.Path("data/uploads")

DEMO = [
    {"id": "it_demo_print", "title": "Framed abstract print, 16x20, black frame", "price": 45.0, "floor": 30.0,
     "condition": "good", "flaws": ["small scuff on the lower left frame edge"],
     "description": ("Framed abstract print, 16 by 20 inches, in a black wood frame with glass. Colors are deep "
                     "teal and rust on a cream ground. Small scuff on the lower left edge of the frame, shown in "
                     "the last photo. Hanging wire attached. Ships boxed with corner protectors, or local pickup "
                     "in Apple Valley, CA."),
     "tags": ["art", "print", "framed", "abstract", "wall art"], "rgb": (32, 96, 104)},
    {"id": "it_demo_lamp", "title": "Brass desk lamp, adjustable arm, works", "price": 28.0, "floor": 18.0,
     "condition": "fair", "flaws": ["tarnish on the base", "cord has a repaired section near the plug"],
     "description": ("Brass desk lamp with an adjustable arm and a 6 foot cord. Tested and working with a standard "
                     "E26 bulb (not included). Tarnish on the base and a repaired section of cord near the plug, "
                     "both pictured. Ships in the continental US or local pickup in Apple Valley, CA."),
     "tags": ["lamp", "brass", "desk", "vintage", "lighting"], "rgb": (140, 110, 40)},
    {"id": "it_demo_jacket", "title": "Canvas work jacket, men's large, lined", "price": 38.0, "floor": 25.0,
     "condition": "good", "flaws": ["faint stain on the right cuff"],
     "description": ("Heavy canvas work jacket, men's size large, quilted lining, four front pockets. Zipper "
                     "and snaps all work. Faint stain on the right cuff, shown close up. Measured flat: 24 inch "
                     "chest, 27 inch length. Ships USPS Priority or local pickup in Apple Valley, CA."),
     "tags": ["jacket", "canvas", "workwear", "mens", "large"], "rgb": (90, 70, 50)},
]


def _png(path: pathlib.Path, rgb: tuple[int, int, int], w: int = 600, h: int = 450) -> None:
    """Write a flat-color PNG with a lighter band, no PIL needed."""
    r, g, b = rgb
    rows = []
    for y in range(h):
        shade = 1.0 if y < h * 0.7 else 1.25
        px = bytes((min(255, int(r * shade)), min(255, int(g * shade)), min(255, int(b * shade))))
        rows.append(b"\x00" + px * w)
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def seed(reset: bool = False) -> list[str]:
    if reset and pathlib.Path("data").exists():
        shutil.rmtree("data")
    store = LocalJSONStore("data")
    made = []
    for d in DEMO:
        if store.get_item(d["id"]) is not None and not reset:
            continue
        photo = UPLOADS / d["id"] / "photo_0.png"
        _png(photo, d["rgb"])
        item = Item(
            id=d["id"], created=time.time(), photo_paths=[str(photo)], status="live",
            curator={"item_name": d["title"], "condition": d["condition"], "visible_flaws": d["flaws"],
                     "confidence": 0.9},
            appraiser={"suggested_list": d["price"], "suggested_floor": d["floor"], "comps": []},
            copywriter={}, title=d["title"], description=d["description"], tags=d["tags"],
            price=d["price"], floor=d["floor"],
        )
        store.save_item(item)
        made.append(d["id"])
    return made


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="wipe data/ first")
    args = ap.parse_args()
    ids = seed(reset=args.reset)
    print(f"seeded {len(ids)} items: {', '.join(ids) or '(none, already present)'}")
