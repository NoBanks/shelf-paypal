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
    """Key sources, in order: GEMINI_KEYS (comma list), GEMINI_API_KEY + GEMINI_API_KEY_N
    env vars (the Windows PC has 43 of them), the keystore file, GOOGLE_API_KEY."""
    ks = os.environ.get("GEMINI_KEYS")
    if ks:
        return [k.strip() for k in ks.split(",") if k.strip()]
    numbered: list[tuple[int, str]] = []
    for name, val in os.environ.items():
        if not val or not val.strip():
            continue
        if name == "GEMINI_API_KEY":
            numbered.append((0, val.strip()))
        elif name.startswith("GEMINI_API_KEY_") and name[15:].isdigit():
            numbered.append((int(name[15:]), val.strip()))
    if numbered:
        return [v for _, v in sorted(numbered)]
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


_BENCHED: dict[str, float] = {}  # key -> time it may be used again
BENCH_SECONDS = 600


def rotate_key(bench_current: bool = False) -> int:
    """Advance to the next usable key. With bench_current=True (after a 429), the key that just
    failed is benched for BENCH_SECONDS so rotation skips it instead of walking into it again.
    Found 2026-10-11: 10 of 44 keys were rate-limited and the walk kept landing on them."""
    import time as _t
    global _KEY_IDX
    keys = _pool()
    if not keys:
        return _KEY_IDX
    now = _t.time()
    if bench_current:
        _BENCHED[keys[_KEY_IDX % len(keys)]] = now + BENCH_SECONDS
    for _ in range(len(keys)):
        _KEY_IDX += 1
        if _BENCHED.get(keys[_KEY_IDX % len(keys)], 0) <= now:
            break
    load_key()
    return _KEY_IDX


def usable_key_count() -> int:
    import time as _t
    now = _t.time()
    return sum(1 for k in _pool() if _BENCHED.get(k, 0) <= now)


async def run_item(photos: list[pathlib.Path], out_dir: pathlib.Path, seller_notes: str = "",
                   on_step=None) -> dict:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from shelf.agents import item_crew, refresh_models

    refresh_models()  # use the key that is current NOW, not the one cached at first use

    runner = InMemoryRunner(agent=item_crew, app_name="shelf")
    session = await runner.session_service.create_session(
        app_name="shelf", user_id="seller"
    )

    prompt = "Photos of ONE item to sell follow. Run the full pipeline."
    if seller_notes.strip():
        prompt += ("\n\nSELLER NOTES (facts from the seller who owns the item; use them as given, "
                   "they override anything you would guess from the photos): " + seller_notes.strip())
    parts = [types.Part.from_text(text=prompt)]
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
        if on_step is not None and event.is_final_response() and event.author in outputs:
            try:
                on_step(event.author, outputs[event.author])
            except Exception:
                pass

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
