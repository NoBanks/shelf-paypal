"""Storage layer for SHELF with local JSON and Firestore backends."""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
from dataclasses import asdict, dataclass, field, fields
from typing import Any


def _new_id() -> str:
    return "it_" + secrets.token_hex(5)


@dataclass
class Item:
    id: str
    created: float
    photo_paths: list[str]
    status: str
    curator: dict
    appraiser: dict
    copywriter: dict
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    price: float = 0.0
    floor: float = 0.0
    sold_price: float = 0.0
    notes: str = ""
    # PayPal (added for the PayPal AI Hackathon build, Oct 2026)
    paypal_order_id: str = ""
    paypal_capture_id: str = ""
    buyer_email: str = ""
    net_amount: float = 0.0
    paid_at: float = 0.0
    tracking_number: str = ""
    carrier: str = ""
    shipped_at: float = 0.0


@dataclass
class LedgerEntry:
    id: str
    item_id: str
    created: float
    kind: str
    amount: float
    memo: str = ""
    paypal_capture_id: str = ""


class BaseStore:
    """Base storage interface."""

    def save_item(self, item: Item) -> None:
        raise NotImplementedError

    def get_item(self, item_id: str) -> Item | None:
        raise NotImplementedError

    def list_items(self, status: str | None = None) -> list[Item]:
        raise NotImplementedError

    def add_ledger(self, entry: LedgerEntry) -> None:
        raise NotImplementedError

    def list_ledger(self) -> list[LedgerEntry]:
        raise NotImplementedError

    def totals(self) -> dict[str, Any]:
        raise NotImplementedError


class LocalJSONStore(BaseStore):
    """Filesystem-backed JSON store."""

    def __init__(self, base_dir: str = "data") -> None:
        self.base_dir = base_dir
        self.items_dir = os.path.join(base_dir, "items")
        self.ledger_path = os.path.join(base_dir, "ledger.jsonl")
        os.makedirs(self.items_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _item_path(self, item_id: str) -> str:
        return os.path.join(self.items_dir, item_id + ".json")

    def _atomic_write(self, path: str, data: str) -> None:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    def save_item(self, item: Item) -> None:
        with self._lock:
            path = self._item_path(item.id)
            self._atomic_write(path, json.dumps(asdict(item), indent=2))

    def get_item(self, item_id: str) -> Item | None:
        with self._lock:
            path = self._item_path(item_id)
            if not os.path.exists(path):
                return None
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        return _item_from(data)

    def list_items(self, status: str | None = None) -> list[Item]:
        items: list[Item] = []
        with self._lock:
            if not os.path.isdir(self.items_dir):
                return []
            for name in os.listdir(self.items_dir):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(self.items_dir, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    items.append(_item_from(data))
                except (json.JSONDecodeError, OSError, TypeError):
                    continue
        if status is not None:
            items = [i for i in items if i.status == status]
        items.sort(key=lambda i: i.created, reverse=True)
        return items

    def add_ledger(self, entry: LedgerEntry) -> None:
        with self._lock:
            line = json.dumps(asdict(entry))
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())

    def list_ledger(self) -> list[LedgerEntry]:
        entries: list[LedgerEntry] = []
        with self._lock:
            if not os.path.exists(self.ledger_path):
                return []
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entries.append(_ledger_from(data))
                    except (json.JSONDecodeError, TypeError):
                        continue
        entries.sort(key=lambda e: e.created, reverse=True)
        return entries

    def totals(self) -> dict[str, Any]:
        items = self.list_items()
        ledger = self.list_ledger()
        listed_count = sum(1 for e in ledger if e.kind == "listed")
        live_count = sum(1 for i in items if i.status == "live")
        sold_count = sum(1 for i in items if i.status in ("sold", "paid", "shipped"))
        gross_sold = sum(i.sold_price for i in items if i.status in ("sold", "paid", "shipped"))
        paid_total = sum(i.sold_price for i in items if i.status in ("paid", "shipped"))
        net_total = sum(i.net_amount for i in items if i.status in ("paid", "shipped"))
        shipped_count = sum(1 for i in items if i.status == "shipped")
        return {
            "listed_count": listed_count,
            "live_count": live_count,
            "sold_count": sold_count,
            "gross_sold": gross_sold,
            "paid_total": paid_total,
            "net_total": net_total,
            "shipped_count": shipped_count,
        }


class FirestoreStore(BaseStore):
    """Firestore-backed store with lazy client import."""

    def __init__(self) -> None:
        from google.cloud import firestore  # type: ignore

        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if project:
            self._client = firestore.Client(project=project)
        else:
            self._client = firestore.Client()
        self._items = self._client.collection("items")
        self._ledger = self._client.collection("ledger")

    def save_item(self, item: Item) -> None:
        self._items.document(item.id).set(asdict(item))

    def get_item(self, item_id: str) -> Item | None:
        doc = self._items.document(item_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        if data is None:
            return None
        return _item_from(data)

    def list_items(self, status: str | None = None) -> list[Item]:
        items: list[Item] = []
        for doc in self._items.stream():
            data = doc.to_dict()
            if data is None:
                continue
            try:
                items.append(_item_from(data))
            except TypeError:
                continue
        if status is not None:
            items = [i for i in items if i.status == status]
        items.sort(key=lambda i: i.created, reverse=True)
        return items

    def add_ledger(self, entry: LedgerEntry) -> None:
        self._ledger.document(entry.id).set(asdict(entry))

    def list_ledger(self) -> list[LedgerEntry]:
        entries: list[LedgerEntry] = []
        for doc in self._ledger.stream():
            data = doc.to_dict()
            if data is None:
                continue
            try:
                entries.append(_ledger_from(data))
            except TypeError:
                continue
        entries.sort(key=lambda e: e.created, reverse=True)
        return entries

    def totals(self) -> dict[str, Any]:
        items = self.list_items()
        ledger = self.list_ledger()
        listed_count = sum(1 for e in ledger if e.kind == "listed")
        live_count = sum(1 for i in items if i.status == "live")
        sold_count = sum(1 for i in items if i.status in ("sold", "paid", "shipped"))
        gross_sold = sum(i.sold_price for i in items if i.status in ("sold", "paid", "shipped"))
        paid_total = sum(i.sold_price for i in items if i.status in ("paid", "shipped"))
        net_total = sum(i.net_amount for i in items if i.status in ("paid", "shipped"))
        shipped_count = sum(1 for i in items if i.status == "shipped")
        return {
            "listed_count": listed_count,
            "live_count": live_count,
            "sold_count": sold_count,
            "gross_sold": gross_sold,
            "paid_total": paid_total,
            "net_total": net_total,
            "shipped_count": shipped_count,
        }


_ITEM_FIELDS = {f.name for f in fields(Item)}
_LEDGER_FIELDS = {f.name for f in fields(LedgerEntry)}


def _item_from(data: dict) -> Item:
    """Build an Item from stored JSON, ignoring keys this version does not know."""
    return Item(**{k: v for k, v in data.items() if k in _ITEM_FIELDS})


def _ledger_from(data: dict) -> LedgerEntry:
    return LedgerEntry(**{k: v for k, v in data.items() if k in _LEDGER_FIELDS})


def get_store() -> BaseStore:
    """Return the configured store backend."""
    if os.environ.get("SHELF_FIRESTORE") == "1":
        return FirestoreStore()
    return LocalJSONStore()


def parse_agent_json(text: str) -> dict:
    """Extract the first JSON object from text using a brace-depth scanner."""
    if not text:
        return {}
    s = text
    i = 0
    n = len(s)
    while i < n:
        if s[i] == "{":
            depth = 0
            start = i
            in_string = False
            escape = False
            while i < n:
                ch = s[i]
                if in_string:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_string = False
                else:
                    if ch == '"':
                        in_string = True
                    elif ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            candidate = s[start : i + 1]
                            try:
                                parsed = json.loads(candidate)
                                if isinstance(parsed, dict):
                                    return parsed
                            except json.JSONDecodeError:
                                pass
                            break
                i += 1
        i += 1
    return {}
