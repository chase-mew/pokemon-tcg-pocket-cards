"""The no-image core payload drops image URLs from the core subset."""
import json

import jsonschema

from constants import (CARDS_JSON_PATH, CORE_RARITIES, V5_CORE_CARDS_PATH,
                       V5_CORE_NO_IMAGE_CARDS_PATH, V5_CORE_NO_IMAGE_CARDS_SCHEMA_PATH)
from database import CORE_NO_IMAGE_FIELDS


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_no_image_covers_the_same_cards_as_core():
    full = _load(CARDS_JSON_PATH)
    core = _load(V5_CORE_CARDS_PATH)
    no_image = _load(V5_CORE_NO_IMAGE_CARDS_PATH)
    kept_ids = {card["id"] for card in full if card["rarity"] in CORE_RARITIES}
    assert kept_ids == {card["id"] for card in core}
    assert kept_ids == {card["id"] for card in no_image}
    assert {card["rarity"] for card in full if card["id"] in kept_ids} == set(CORE_RARITIES)


def test_no_image_matches_schema_and_field_count():
    no_image = _load(V5_CORE_NO_IMAGE_CARDS_PATH)
    schema = _load(V5_CORE_NO_IMAGE_CARDS_SCHEMA_PATH)
    jsonschema.validate(instance=no_image, schema=schema)
    assert all(tuple(card) == CORE_NO_IMAGE_FIELDS for card in no_image)
