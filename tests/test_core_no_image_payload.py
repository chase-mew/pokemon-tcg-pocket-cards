"""The no-image core payload drops image URLs from the sparse core subset."""
import json

import jsonschema

from constants import (CARDS_JSON_PATH, CORE_RARITIES, V5_CORE_CARDS_PATH,
                       V5_CORE_NO_IMAGE_CARDS_PATH, V5_CORE_NO_IMAGE_CARDS_SCHEMA_PATH,
                       is_playable_trainer)


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


def test_no_image_matches_its_schema():
    no_image = _load(V5_CORE_NO_IMAGE_CARDS_PATH)
    schema = _load(V5_CORE_NO_IMAGE_CARDS_SCHEMA_PATH)
    jsonschema.validate(instance=no_image, schema=schema)


def test_no_image_records_are_core_minus_image():
    core = _load(V5_CORE_CARDS_PATH)
    no_image = _load(V5_CORE_NO_IMAGE_CARDS_PATH)
    by_id = {record["id"]: record for record in core}
    for record in no_image:
        assert record == {key: value for key, value in by_id[record["id"]].items()
                          if key != "image"}


def test_no_image_trainer_records_omit_ex_and_mega():
    no_image = _load(V5_CORE_NO_IMAGE_CARDS_PATH)
    for record in no_image:
        if record["type"] == "Trainer":
            assert "ex" not in record
            assert "mega" not in record
            if not is_playable_trainer(record["name"]):
                assert "stage" not in record
                assert "health" not in record
                assert "points" not in record


def test_no_image_tagged_card_carries_special_tags():
    no_image = _load(V5_CORE_NO_IMAGE_CARDS_PATH)
    record = next(r for r in no_image if r["id"] == "a3-088")
    assert record["special_tags"] == ["ultra_beasts"]
