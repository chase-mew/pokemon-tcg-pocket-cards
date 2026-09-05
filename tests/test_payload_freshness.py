"""Every committed payload must equal what its builder produces today.

The suite validated shape and cross-payload consistency but never
provenance, so a builder change that left the data behind passed
unnoticed. These two checks compare bytes against a fresh build.
"""
import json
import os

import pytest

import projections as P
import database
from utils import minified_path
from constants import V5_DIR


@pytest.fixture(scope="module")
def cards():
    return database.read_all_v5_cards()


TRADE_FIELDS = ("tradable", "sharable", "trade_cost")


def test_full_carries_the_trading_fields():
    """collection and full both carry them; the projections that drop
    them are core and gameplay. Documented in docs/payloads.md."""
    with open(os.path.join(V5_DIR, "cards.json"), encoding="utf-8") as f:
        full = json.load(f)
    assert full, "full payload is empty"
    missing = [key for key in TRADE_FIELDS
               if any(key not in record for record in full)]
    assert not missing, f"full is missing {missing}; check payloads.md"


def test_read_order_is_stable_across_filesystems():
    """The payloads are built from this list, so its order must not
    depend on the filesystem. Sorted is the order the data ships in."""
    order = [card["set_code"] for card in database.read_all_v5_cards()]
    assert order == sorted(order), "read_all_v5_cards returned filesystem order"


def _pretty(records):
    return json.dumps(records, indent=2, ensure_ascii=False)


def _minified(records):
    return json.dumps(records, separators=(",", ":"), ensure_ascii=False)


def test_root_payloads_match_a_fresh_build(cards):
    stale = []
    for _variant, _url_stem, filename, build in P.SHARD_VARIANTS:
        records = build(cards)
        root_path = os.path.join(V5_DIR, filename)
        for path, dumped in ((root_path, _pretty(records)),
                             (minified_path(root_path), _minified(records))):
            with open(path, "r", encoding="utf-8") as f:
                if f.read() != dumped:
                    stale.append(os.path.basename(path))
    assert not stale, (
        "committed payloads differ from a fresh build; re-run "
        "compile_projections: " + ", ".join(stale))


def test_shards_match_a_fresh_build(cards):
    stale = []
    for variant, _url_stem, _root_path, build in P.SHARD_VARIANTS:
        by_set = {}
        for record in build(cards):
            by_set.setdefault(record["set_code"], []).append(record)
        for prefix, group in by_set.items():
            for minified, dumped in ((False, _pretty(group)),
                                     (True, _minified(group))):
                path = P.shard_path(prefix, variant, V5_DIR, minified)
                with open(path, "r", encoding="utf-8") as f:
                    if f.read() != dumped:
                        stale.append(os.path.relpath(path, V5_DIR))
    assert not stale, (
        f"{len(stale)} shards differ from a fresh build: {sorted(stale)[:6]}")
