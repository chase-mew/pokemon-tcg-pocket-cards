"""The core payload is a sparse gameplay-only subset of the full dataset."""
import json
import os

import jsonschema

from constants import (CARDS_JSON_PATH, CORE_RARITIES, V5_CORE_CARDS_PATH,
                       V5_CORE_CARDS_SCHEMA_PATH)
from database import CORE_FIELDS


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _is_fossil(record):
    return record["type"] == "Trainer" and record["name"].endswith("Fossil")


def test_core_payload_covers_every_gameplay_card():
    full = _load(CARDS_JSON_PATH)
    core = _load(V5_CORE_CARDS_PATH)
    kept = {card["id"] for card in full if card["rarity"] in CORE_RARITIES}
    assert {card["id"] for card in core} == kept


def test_core_records_omit_inapplicable_keys():
    """A record keeps exactly the core fields the full card fills, minus the
    ex and mega keys Trainer cards always omit."""
    full = _load(CARDS_JSON_PATH)
    core = _load(V5_CORE_CARDS_PATH)
    by_id = {card["id"]: card for card in full}
    for record in core:
        source = by_id[record["id"]]
        expected = {field for field in CORE_FIELDS if source.get(field) is not None}
        if source["type"] == "Trainer":
            expected -= {"ex", "mega"}
        assert set(record) == expected


def test_core_present_values_match_the_full_payload():
    full = _load(CARDS_JSON_PATH)
    core = _load(V5_CORE_CARDS_PATH)
    by_id = {card["id"]: card for card in full}
    for record in core:
        source = by_id[record["id"]]
        for field in record:
            assert record[field] == source.get(field)


def test_core_records_never_carry_null_values():
    core = _load(V5_CORE_CARDS_PATH)
    assert not any(record[key] is None for record in core for key in record)


def test_core_fossil_items_keep_playable_fields():
    core = _load(V5_CORE_CARDS_PATH)
    fossils = [record for record in core if _is_fossil(record)]
    assert fossils
    for record in fossils:
        assert record["stage"] == "Basic"
        assert record["health"] == 40
        assert record["points"] == 1
        assert "ex" not in record
        assert "mega" not in record


def test_core_payload_is_smaller_than_the_full_payload():
    full_size = os.path.getsize(CARDS_JSON_PATH.replace(".json", ".min.json"))
    core_size = os.path.getsize(V5_CORE_CARDS_PATH.replace(".json", ".min.json"))
    assert core_size < full_size * 0.4


def test_core_payload_matches_its_schema():
    core = _load(V5_CORE_CARDS_PATH)
    schema = _load(V5_CORE_CARDS_SCHEMA_PATH)
    jsonschema.validate(instance=core, schema=schema)


def test_core_payload_excludes_cosmetic_rarities():
    core = _load(V5_CORE_CARDS_PATH)
    rarities = {card["rarity"] for card in core}
    assert rarities == set(CORE_RARITIES)


def test_core_payload_drops_no_unique_gameplay_cards():
    full = _load(CARDS_JSON_PATH)
    core = _load(V5_CORE_CARDS_PATH)
    kept_ids = {card["id"] for card in core}
    kept_builder_numbers = {card["deckBuilderNr"] for card in core}
    excluded = [card for card in full if card["id"] not in kept_ids]
    assert excluded
    for card in excluded:
        assert card["deckBuilderNr"] in kept_builder_numbers
