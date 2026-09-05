"""The no-image gameplay payload keeps today's shape with the image URL dropped."""
import json

import jsonschema

from constants import (CARDS_JSON_PATH, CORE_RARITIES, V5_GAMEPLAY_CARDS_PATH,
                       V5_GAMEPLAY_NO_IMAGE_CARDS_PATH,
                       V5_GAMEPLAY_NO_IMAGE_CARDS_SCHEMA_PATH, is_playable_trainer)

NON_FOSSIL_TRAINER_KEYS = {"id", "name", "set_code", "type", "subtype",
                           "card_text", "deckBuilderNr"}
FOSSIL_TRAINER_KEYS = {"id", "name", "set_code", "type", "subtype", "stage",
                       "health", "points", "weakness", "card_text",
                       "deckBuilderNr"}


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)



def test_no_image_covers_the_same_cards_as_gameplay():
    full = _load(CARDS_JSON_PATH)
    gameplay = _load(V5_GAMEPLAY_CARDS_PATH)
    no_image = _load(V5_GAMEPLAY_NO_IMAGE_CARDS_PATH)
    kept_ids = {card["id"] for card in full if card["rarity"] in CORE_RARITIES}
    assert kept_ids == {card["id"] for card in gameplay}
    assert kept_ids == {card["id"] for card in no_image}


def test_no_image_matches_its_schema():
    no_image = _load(V5_GAMEPLAY_NO_IMAGE_CARDS_PATH)
    schema = _load(V5_GAMEPLAY_NO_IMAGE_CARDS_SCHEMA_PATH)
    jsonschema.validate(instance=no_image, schema=schema)


def test_no_image_records_are_gameplay_minus_image():
    gameplay = _load(V5_GAMEPLAY_CARDS_PATH)
    no_image = _load(V5_GAMEPLAY_NO_IMAGE_CARDS_PATH)
    by_id = {record["id"]: record for record in gameplay}
    for record in no_image:
        assert record == {key: value for key, value in by_id[record["id"]].items()
                          if key != "image"}


def test_no_image_records_carry_no_image_key():
    no_image = _load(V5_GAMEPLAY_NO_IMAGE_CARDS_PATH)
    assert not any("image" in record for record in no_image)


def test_no_image_trainer_shapes_follow_trim_rule():
    no_image = _load(V5_GAMEPLAY_NO_IMAGE_CARDS_PATH)
    for record in no_image:
        if record["type"] != "Trainer":
            continue
        if is_playable_trainer(record["name"]):
            assert set(record) == FOSSIL_TRAINER_KEYS
            assert record["weakness"] == "none"
        else:
            assert set(record) == NON_FOSSIL_TRAINER_KEYS
