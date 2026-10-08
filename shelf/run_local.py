"""SHELF local runner (M1): folder of item photos -> draft listing JSON.

Usage: python -m shelf.run_local <photo_dir_or_files...> [--out out/]
Loads a Gemini API key from the local key store into the process env (never
printed). Runs the item_crew (curator -> appraiser -> copywriter) with the
photos as multimodal input; writes each agent's output + the final listing.
"""
import argparse
import asyncio
import json
import os
import pathlib
import sys

KEYSTORE = os.path.expanduser("~/.openclaw/gemini-keys.json")

# KEY ROTATION (2026-08-19): the original loader pinned key[0] (or the single
# Cloud Run GOOGLE_API_KEY env) and STARVED on quota while 42 fresh keys sat
# idle - the 8/18 overnight feed failed 21 straight waves because of it.
# TINP's nightly flow rotates and never starves. Do not revert to single-key.
import random as _random
_KEY_IDX = _random.randint(0, 997)  # random pool entry; per-item rotation walks forward from here


def _pool() -> list[str]:
    ks = os.environ.get("GEMINI_KEYS")
    if ks:
        return [k.strip() for k in ks.split(",") if k.strip()]
    try:
        with open(KEYSTORE) as fh:
            return json.load(fh)["keys"]
    except Exception:
        k = os.environ.get("GOOGLE_API_KEY")
        return [k] if k else []


def load_key(idx: int | None = None) -> None:
    global _KEY_IDX
    keys = _pool()
    if not keys:
        return
    if idx is not None:
        _KEY_IDX = idx
    os.environ["GOOGLE_API_KEY"] = keys[_KEY_IDX % len(keys)]
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")


def rotate_key() -> int:
    """Advance to the next key in the pool (call on 429/503/quota errors)."""
    global _KEY_IDX
    _KEY_IDX += 1
    load_key()
    return _KEY_IDX


async def run_item(photos: list[pathlib.Path], out_dir: pathlib.Path) -> dict:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from shelf.agents import item_crew

    runner = InMemoryRunner(agent=item_crew, app_name="shelf")
    session = await runner.session_service.create_session(
        app_name="shelf", user_id="seller"
    )

    parts = [types.Part.from_text(text=(
        "Photos of ONE item to sell follow. Run the full pipeline."))]
    for p in photos:
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        parts.append(types.Part.from_bytes(data=p.read_bytes(), mime_type=mime))
    msg = types.Content(role="user", parts=parts)

    outputs: dict[str, str] = {}
    async for event in runner.run_async(
        user_id="seller", session_id=session.id, new_message=msg
    ):
        if event.content and event.content.parts:
            text = "".join(pt.text or "" for pt in event.content.parts)
            if text.strip():
                outputs[event.author] = outputs.get(event.author, "") + text

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "crew_output.json").write_text(json.dumps(outputs, indent=1))
    return outputs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("photos", nargs="+")
    ap.add_argument("--out", default="out/item1")
    ap.add_argument("--key-index", type=int, default=0)
    args = ap.parse_args()

    load_key(args.key_index)
    photos = []
    for p in args.photos:
        pp = pathlib.Path(p).expanduser()
        if pp.is_dir():
            photos += sorted(
                x for x in pp.iterdir() if x.suffix.lower() in (".jpg", ".jpeg", ".png")
            )
        else:
            photos.append(pp)
    if not photos:
        sys.exit("no photos found")
    print(f"running crew on {len(photos)} photo(s)...")
    outputs = asyncio.run(run_item(photos, pathlib.Path(args.out)))
    for author, text in outputs.items():
        print(f"\n=== {author.upper()} ===")
        print(text[:1200])


if __name__ == "__main__":
    main()
