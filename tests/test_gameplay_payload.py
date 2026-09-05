"""The gameplay payload carries combat data for the gameplay rarities."""
import json

import jsonschema

from constants import (CARDS_JSON_PATH, CORE_RARITIES, GAMEPLAY_FIELDS,
                       V5_CORE_CARDS_PATH, V5_GAMEPLAY_CARDS_PATH,
                       V5_GAMEPLAY_CARDS_SCHEMA_PATH)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_gameplay_covers_the_same_cards_as_core():
    full = _load(CARDS_JSON_PATH)
    core = _load(V5_CORE_CARDS_PATH)
    gameplay = _load(V5_GAMEPLAY_CARDS_PATH)
    kept_ids = {card["id"] for card in full if card["rarity"] in CORE_RARITIES}
    assert kept_ids == {card["id"] for card in core}
    assert kept_ids == {card["id"] for card in gameplay}
    assert {card["rarity"] for card in full if card["id"] in kept_ids} == set(CORE_RARITIES)


def test_gameplay_matches_schema_and_field_count():
    gameplay = _load(V5_GAMEPLAY_CARDS_PATH)
    schema = _load(V5_GAMEPLAY_CARDS_SCHEMA_PATH)
    jsonschema.validate(instance=gameplay, schema=schema)
    assert all(tuple(card) == GAMEPLAY_FIELDS for card in gameplay)
