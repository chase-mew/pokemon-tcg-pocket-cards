"""The gameplay payload is a sparse subset carrying combat data for gameplay rarities."""
import json

import jsonschema

from constants import (CARDS_JSON_PATH, CORE_RARITIES, GAMEPLAY_FIELDS,
                       V5_CORE_CARDS_PATH, V5_GAMEPLAY_CARDS_PATH,
                       V5_GAMEPLAY_CARDS_SCHEMA_PATH)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _is_fossil(record):
    return record["type"] == "Trainer" and record["name"].endswith("Fossil")


def test_gameplay_covers_the_same_cards_as_core():
    full = _load(CARDS_JSON_PATH)
    core = _load(V5_CORE_CARDS_PATH)
    gameplay = _load(V5_GAMEPLAY_CARDS_PATH)
    kept_ids = {card["id"] for card in full if card["rarity"] in CORE_RARITIES}
    assert kept_ids == {card["id"] for card in core}
    assert kept_ids == {card["id"] for card in gameplay}
    assert {card["rarity"] for card in full if card["id"] in kept_ids} == set(CORE_RARITIES)


def test_gameplay_matches_its_schema():
    gameplay = _load(V5_GAMEPLAY_CARDS_PATH)
    schema = _load(V5_GAMEPLAY_CARDS_SCHEMA_PATH)
    jsonschema.validate(instance=gameplay, schema=schema)


def test_gameplay_records_omit_inapplicable_keys():
    """A record keeps exactly the gameplay fields the full card fills, minus
    the ex and mega keys Trainer cards always omit."""
    full = _load(CARDS_JSON_PATH)
    gameplay = _load(V5_GAMEPLAY_CARDS_PATH)
    by_id = {card["id"]: card for card in full}
    for record in gameplay:
        source = by_id[record["id"]]
        expected = {field for field in GAMEPLAY_FIELDS if source.get(field) is not None}
        if source["type"] == "Trainer":
            expected -= {"ex", "mega"}
        assert set(record) == expected


def test_gameplay_trainer_records_omit_combat_keys():
    gameplay = _load(V5_GAMEPLAY_CARDS_PATH)
    for record in gameplay:
        if record["type"] != "Trainer":
            continue
        assert "ex" not in record
        assert "mega" not in record
        assert "retreat" not in record
        assert "weakness" not in record
        assert "evolves_from" not in record
        if not _is_fossil(record):
            assert "stage" not in record
            assert "health" not in record
            assert "points" not in record
        else:
            assert record["stage"] == "Basic"
            assert record["health"] == 40
            assert record["points"] == 1
