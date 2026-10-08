"""Deterministic publisher and bookkeeper for SHELF items."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shelf.store import Item, LedgerEntry, parse_agent_json

if TYPE_CHECKING:
    from shelf.store import BaseStore


def _parse_copywriter(text: str) -> tuple[str, str, list[str]]:
    """Extract title, description, and tags from copywriter output.

    Expected format (case-insensitive, order-tolerant):
        Title: ...
        Description: ...
        Tags: a, b, c

    Falls back to using the whole text as description if parsing fails.
    """
    title = ""
    description = ""
    tags: list[str] = []

    if not text:
        return title, description, tags

    lines = text.splitlines()
    title_idx: int | None = None
    desc_idx: int | None = None
    tags_idx: int | None = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("title:") and title_idx is None:
            title_idx = i
        elif lower.startswith("description:") and desc_idx is None:
            desc_idx = i
        elif lower.startswith("tags:") and tags_idx is None:
            tags_idx = i

    if title_idx is not None:
        title = lines[title_idx].split(":", 1)[1].strip()

    if desc_idx is not None:
        inline = lines[desc_idx].split(":", 1)[1].strip()
        if tags_idx is not None and tags_idx > desc_idx:
            desc_lines = lines[desc_idx + 1 : tags_idx]
        else:
            desc_lines = lines[desc_idx + 1 :]
        tail = "\n".join(desc_lines).strip()
        description = (inline + ("\n" + tail if tail else "")).strip()

    if tags_idx is not None:
        tags_part = lines[tags_idx].split(":", 1)[1].strip()
        tags = [t.strip() for t in tags_part.split(",") if t.strip()]

    if not title and not description and not tags:
        # LABEL-FREE FALLBACK (2026-08-20, bug #3 caught filming the demo): the
        # model sometimes returns "Title line\n\nBody..." with no Title:/
        # Description: labels. The old fallback dumped everything into
        # description, leaving title empty -> "(processing)" shown on the live
        # store. Treat a short first line followed by a body as the title.
        stripped = text.strip()
        first, _, rest = stripped.partition("\n")
        if first.strip() and len(first.strip()) <= 90 and rest.strip():
            title = first.strip()
            description = rest.strip()
        else:
            description = stripped

    return title, description, tags


def build_item_from_crew(
    item_id: str,
    photo_paths: list[str],
    crew: dict,
) -> Item:
    """Build an Item from crew agent outputs.

    Args:
        item_id: The item identifier.
        photo_paths: List of saved photo file paths.
        crew: Dict keyed by agent name ("curator", "appraiser", "copywriter")
            with text outputs.

    Returns:
        A new Item with status "draft".
    """
    import time

    curator_text = crew.get("curator", "")
    appraiser_text = crew.get("appraiser", "")
    copywriter_text = crew.get("copywriter", "")

    curator = parse_agent_json(curator_text)
    appraiser = parse_agent_json(appraiser_text)

    title, description, tags = _parse_copywriter(copywriter_text)

    def _to_price(v) -> float:
        # Tolerant coercion (2026-08-19): lite models return "$45" / "40-50"
        # strings or alternate keys; a strict isinstance check silently gave
        # every item price 0.0. Take the first number found.
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            import re
            m = re.search(r"\d+(?:\.\d+)?", v.replace(",", ""))
            if m:
                return float(m.group())
        return 0.0

    price = 0.0
    floor = 0.0
    if isinstance(appraiser, dict):
        for k in ("suggested_list", "list_price", "price", "suggested_price"):
            if appraiser.get(k) is not None:
                price = _to_price(appraiser.get(k))
                if price:
                    break
        for k in ("suggested_floor", "floor_price", "floor", "minimum_price"):
            if appraiser.get(k) is not None:
                floor = _to_price(appraiser.get(k))
                if floor:
                    break

    # HERO ORDERING (2026-08-19, Ryan's law): the curator SEES the photos and
    # picks which one sells the item - never lead with the back of a frame.
    try:
        hi = int(float(str(appraiser.get("hero_index", curator.get("hero_index", 0))
                           if isinstance(appraiser, dict) else curator.get("hero_index", 0))))
        if isinstance(curator, dict) and curator.get("hero_index") is not None:
            hi = int(float(str(curator.get("hero_index"))))
        if 0 < hi < len(photo_paths):
            photo_paths = [photo_paths[hi]] + [pp for j, pp in enumerate(photo_paths) if j != hi]
    except Exception:
        pass

    return Item(
        id=item_id,
        created=time.time(),
        photo_paths=list(photo_paths),
        status="draft",
        curator=curator if isinstance(curator, dict) else {},
        appraiser=appraiser if isinstance(appraiser, dict) else {},
        copywriter={},
        title=title,
        description=description,
        tags=tags,
        price=price,
        floor=floor,
        sold_price=0.0,
        notes="",
    )


def approve(store: "BaseStore", item_id: str) -> Item:
    """Transition an item from draft to live and record a ledger entry.

    Args:
        store: The storage backend.
        item_id: The item identifier.

    Returns:
        The updated Item.

    Raises:
        KeyError: If the item does not exist.
        ValueError: If the item is not in "draft" status.
    """
    import secrets
    import time

    item = store.get_item(item_id)
    if item is None:
        raise KeyError(f"item not found: {item_id}")
    if item.status != "draft":
        raise ValueError(f"cannot approve item in status {item.status!r}")

    item.status = "live"
    store.save_item(item)

    entry = LedgerEntry(
        id="le_" + secrets.token_hex(5),
        item_id=item_id,
        created=time.time(),
        kind="listed",
        amount=item.price,
        memo=item.title,
    )
    store.add_ledger(entry)

    return item


def mark_sold(store: "BaseStore", item_id: str, sold_price: float) -> Item:
    """Transition an item from live to sold and record a ledger entry.

    Args:
        store: The storage backend.
        item_id: The item identifier.
        sold_price: The price at which the item sold.

    Returns:
        The updated Item.

    Raises:
        KeyError: If the item does not exist.
        ValueError: If the item is not in "live" status.
    """
    import secrets
    import time

    item = store.get_item(item_id)
    if item is None:
        raise KeyError(f"item not found: {item_id}")
    if item.status != "live":
        raise ValueError(f"cannot mark sold item in status {item.status!r}")

    item.status = "sold"
    item.sold_price = float(sold_price)
    store.save_item(item)

    entry = LedgerEntry(
        id="le_" + secrets.token_hex(5),
        item_id=item_id,
        created=time.time(),
        kind="sold",
        amount=float(sold_price),
        memo=item.title,
    )
    store.add_ledger(entry)

    return item


def mark_paid(store: "BaseStore", item_id: str) -> Item:
    """Transition an item from sold to paid and record a ledger entry.

    Args:
        store: The storage backend.
        item_id: The item identifier.

    Returns:
        The updated Item.

    Raises:
        KeyError: If the item does not exist.
        ValueError: If the item is not in "sold" status.
    """
    import secrets
    import time

    item = store.get_item(item_id)
    if item is None:
        raise KeyError(f"item not found: {item_id}")
    if item.status != "sold":
        raise ValueError(f"cannot mark paid item in status {item.status!r}")

    item.status = "paid"
    store.save_item(item)

    entry = LedgerEntry(
        id="le_" + secrets.token_hex(5),
        item_id=item_id,
        created=time.time(),
        kind="paid",
        amount=item.sold_price,
        memo=item.title,
    )
    store.add_ledger(entry)

    return item
