"""Smoke tests for SHELF M2 storage and publish layers."""

import json
import time
from pathlib import Path

import pytest

from shelf import publish, store


@pytest.fixture
def tmp_store(tmp_path: Path) -> store.LocalJSONStore:
    return store.LocalJSONStore(str(tmp_path))


def _make_item(item_id: str, status: str = "draft", price: float = 10.0) -> store.Item:
    return store.Item(
        id=item_id,
        created=time.time(),
        photo_paths=[],
        status=status,
        curator={},
        appraiser={},
        copywriter={},
        title="Test Item",
        description="A test item.",
        tags=["test"],
        price=price,
        floor=price * 0.5,
    )


def test_local_store_round_trip(tmp_store: store.LocalJSONStore) -> None:
    item = _make_item("it_aaaaaaaaaa", price=25.0)
    tmp_store.save_item(item)

    fetched = tmp_store.get_item("it_aaaaaaaaaa")
    assert fetched is not None
    assert fetched.id == "it_aaaaaaaaaa"
    assert fetched.title == "Test Item"
    assert fetched.price == 25.0
    assert fetched.status == "draft"

    items = tmp_store.list_items()
    assert len(items) == 1
    assert items[0].id == "it_aaaaaaaaaa"

    listed = tmp_store.list_items(status="draft")
    assert len(listed) == 1

    other = tmp_store.list_items(status="live")
    assert len(other) == 0


def test_local_store_ledger_and_totals(tmp_store: store.LocalJSONStore) -> None:
    item_a = _make_item("it_aaaaaaaaaa", status="live", price=20.0)
    item_b = _make_item("it_bbbbbbbbbb", status="sold", price=30.0)
    item_b.sold_price = 30.0
    item_c = _make_item("it_cccccccccc", status="paid", price=40.0)
    item_c.sold_price = 40.0
    tmp_store.save_item(item_a)
    tmp_store.save_item(item_b)
    tmp_store.save_item(item_c)

    tmp_store.add_ledger(store.LedgerEntry(
        id="le_1111111111",
        item_id="it_aaaaaaaaaa",
        created=time.time(),
        kind="listed",
        amount=20.0,
        memo="Test Item",
    ))
    tmp_store.add_ledger(store.LedgerEntry(
        id="le_2222222222",
        item_id="it_bbbbbbbbbb",
        created=time.time(),
        kind="sold",
        amount=30.0,
        memo="Test Item",
    ))
    tmp_store.add_ledger(store.LedgerEntry(
        id="le_3333333333",
        item_id="it_cccccccccc",
        created=time.time(),
        kind="paid",
        amount=40.0,
        memo="Test Item",
    ))

    ledger = tmp_store.list_ledger()
    assert len(ledger) == 3

    totals = tmp_store.totals()
    assert totals["listed_count"] == 1
    assert totals["live_count"] == 1
    assert totals["sold_count"] == 2
    assert totals["gross_sold"] == 70.0
    assert totals["paid_total"] == 40.0



def test_parse_agent_json_fenced() -> None:
    text = "Here is the result:\n```json\n{\"item_name\": \"Lamp\", \"condition\": \"good\"}\n```\nDone."
    out = store.parse_agent_json(text)
    assert out == {"item_name": "Lamp", "condition": "good"}


def test_parse_agent_json_plain() -> None:
    text = "prefix {\"a\": 1, \"b\": {\"c\": [1, 2]}} suffix"
    out = store.parse_agent_json(text)
    assert out == {"a": 1, "b": {"c": [1, 2]}}


def test_parse_agent_json_junk() -> None:
    assert store.parse_agent_json("no json here at all") == {}
    assert store.parse_agent_json("{broken: json,,,") == {}


def _fixture_crew() -> dict:
    return {
        "curator": "```json\n{\"item_name\": \"Blue Vase\", \"category\": \"Decor\", \"condition\": \"good\", \"visible_flaws\": [\"small chip\"]}\n```",
        "appraiser": "{\"suggested_list\": 25.0, \"suggested_floor\": 15.0, \"comps\": []}",
        "copywriter": "Title: Blue Ceramic Vase\n\nDescription: A lovely blue vase with a small chip, disclosed honestly.\n\nTags: vase, decor, blue, ceramic",
    }


def test_build_item_from_crew(tmp_path) -> None:
    item = publish.build_item_from_crew("it_abc123def0", ["/tmp/p1.jpg"], _fixture_crew())
    assert item.status == "draft"
    assert item.title == "Blue Ceramic Vase"
    assert "chip" in item.description
    assert item.price == 25.0
    assert item.floor == 15.0
    assert "vase" in [t.strip() for t in item.tags]


def test_transitions(tmp_path) -> None:
    s = store.LocalJSONStore(str(tmp_path))
    item = publish.build_item_from_crew("it_abc123def1", [], _fixture_crew())
    s.save_item(item)
    live = publish.approve(s, item.id)
    assert live.status == "live"
    sold = publish.mark_sold(s, item.id, 22.0)
    assert sold.status == "sold" and sold.sold_price == 22.0
    paid = publish.mark_paid(s, item.id)
    assert paid.status == "paid"
    kinds = [e.kind for e in s.list_ledger()]
    assert "listed" in kinds and "sold" in kinds and "paid" in kinds
