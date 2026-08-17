import re

REQ_KEYS = {
    "id", "name", "set_code", "set_name", "pack", "release_date",
    "type", "subtype", "stage", "evolves_from", "rarity", "pack_points",
    "ex", "mega", "shiny", "special_tags", "art_style",
    "health", "retreat", "weakness", "ability", "card_text",
    "attacks", "points", "deckBuilderNr", "artist",
    "image", "image_png", "flavour_text", "alternate_versions"
}


def test_v5_schema_and_types(cards):
    assert cards, "No cards loaded"
    seen = set()
    for c in cards:
        assert set(c.keys()) == REQ_KEYS, f"Schema mismatch on {c.get('id')}"
        assert re.match(r"^[a-z][a-z0-9]*-\d{1,3}$", c["id"]), f"Bad ID {c['id']}"
        assert c["id"] not in seen, f"Duplicate ID {c['id']}"
        seen.add(c["id"])

        assert c["type"] in ("Pokémon", "Trainer")
        assert isinstance(c["health"], (int, type(None)))
        assert isinstance(c["retreat"], (int, type(None)))
        assert isinstance(c["points"], (int, type(None)))
        assert isinstance(c["pack_points"], (int, type(None)))
        assert isinstance(c["ability"], dict) and isinstance(c["attacks"], dict)
        assert type(c["ex"]) is bool and type(c["mega"]) is bool and type(c["shiny"]) is bool