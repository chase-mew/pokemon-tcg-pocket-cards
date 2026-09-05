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


def _pretty(records):
    return json.dumps(records, indent=2, ensure_ascii=False)


def _minified(records):
    return json.dumps(records, separators=(",", ":"), ensure_ascii=False)


def test_root_payloads_match_a_fresh_build(cards):
    stale = []
    for _variant, _url_stem, root_path, build in P.SHARD_VARIANTS:
        records = build(cards)
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
