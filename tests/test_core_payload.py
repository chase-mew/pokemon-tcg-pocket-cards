"""The core payload is a faithful projection of the full v5 dataset."""
import json
import os

from constants import CARDS_JSON_PATH, V5_CORE_CARDS_PATH
from database import CORE_FIELDS


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_core_payload_covers_every_card():
    full = _load(CARDS_JSON_PATH)
    core = _load(V5_CORE_CARDS_PATH)
    assert len(core) == len(full)


def test_core_records_carry_exactly_the_core_fields():
    core = _load(V5_CORE_CARDS_PATH)
    for record in core[:50]:
        assert tuple(record.keys()) == CORE_FIELDS


def test_core_values_match_the_full_payload():
    full = _load(CARDS_JSON_PATH)
    core = _load(V5_CORE_CARDS_PATH)
    by_id = {card["id"]: card for card in full}
    for record in core:
        source = by_id[record["id"]]
        for field in CORE_FIELDS:
            assert record[field] == source.get(field)


def test_core_payload_is_smaller_than_the_full_payload():
    full_size = os.path.getsize(CARDS_JSON_PATH.replace(".json", ".min.json"))
    core_size = os.path.getsize(V5_CORE_CARDS_PATH.replace(".json", ".min.json"))
    assert core_size < full_size * 0.4
