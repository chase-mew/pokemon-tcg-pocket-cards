"""Unit tests for the pure helpers in utils.py and deck_code.py."""
import base64

import pytest

from deck_code import SPECIAL_THRESHOLD, TRAINER_OFFSET, create_deck_code, get_deck_builder_nr
from utils import (clean_text, compile_tag_matchers, normalise_set_code, parse_release_date,
                   parse_trainer_subtype, serebii_slug, set_code_to_prefix, slugify, to_int)


class TestSetCodes:
    @pytest.mark.parametrize("raw,expected", [
        ("pa", "P-A"), ("PA", "P-A"), ("P-A", "P-A"), ("p-b", "P-B"),
        ("a1", "A1"), ("A1", "A1"), ("a2a", "A2A"), (" b3b ", "B3B"),
    ])
    def test_normalise(self, raw, expected):
        assert normalise_set_code(raw) == expected

    @pytest.mark.parametrize("code,prefix", [
        ("P-A", "pa"), ("P-B", "pb"), ("A1", "a1"), ("B2b", "b2b"), ("b10", "b10"),
    ])
    def test_prefix(self, code, prefix):
        assert set_code_to_prefix(code) == prefix

    def test_normalise_is_idempotent(self):
        for raw in ("pa", "a1", "A2a", "P-B"):
            once = normalise_set_code(raw)
            assert normalise_set_code(once) == once


class TestTextHelpers:
    @pytest.mark.parametrize("raw,expected", [
        ("  Charizard\n  ex  ", "Charizard ex"),
        ("a\t\tb", "a b"),
        ("   ", None),
        ("", None),
        (None, None),
    ])
    def test_clean_text(self, raw, expected):
        assert clean_text(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("40 HP", 40), ("100+", 100), ("30x", 30), ("#66", 66), ("", None), (None, None),
    ])
    def test_to_int(self, raw, expected):
        assert to_int(raw) == expected

    def test_to_int_default(self):
        assert to_int("no digits", default=0) == 0

    @pytest.mark.parametrize("name,expected", [
        ("Mr. Mime", "mrmime"), ("Ho-Oh", "hooh"), ("Premium Missions", "premiummissions"),
    ])
    def test_slugify(self, name, expected):
        assert slugify(name) == expected

    def test_serebii_slug_keeps_hyphens(self):
        assert serebii_slug("Ho-Oh") == "ho-oh" and serebii_slug("Mr. Mime") == "mrmime"

    @pytest.mark.parametrize("line,expected", [
        ("Trainer - Pokemon Tool", "Tool"),
        ("Trainer - Supporter", "Supporter"),
        ("Trainer - Item", "Item"),
        ("Trainer - Stadium", "Stadium"),
        ("Trainer", None),
    ])
    def test_trainer_subtype(self, line, expected):
        assert parse_trainer_subtype(line) == expected


class TestReleaseDate:
    def test_parses_the_index_format(self):
        assert parse_release_date("30 Jun 26") == "2026-06-30"

    @pytest.mark.parametrize("blank", [None, "", "   "])
    def test_blank_is_none(self, blank):
        assert parse_release_date(blank) is None

    def test_unparsable_date_raises(self):
        with pytest.raises(ValueError):
            parse_release_date("June 30th")


class TestTagMatchers:
    def test_matches_are_case_insensitive_and_bounded(self):
        matchers = compile_tag_matchers({"ancient": ["Great Tusk", "Sada"]})
        assert matchers["ancient"].search("great tusk ex")
        assert matchers["ancient"].search("Sada's Vitality")
        assert not matchers["ancient"].search("Sadaharu")

    def test_regex_metacharacters_in_names_are_escaped(self):
        matchers = compile_tag_matchers({"weird": ["Mr. Mime"]})
        assert matchers["weird"].search("Mr. Mime")
        assert not matchers["weird"].search("MrXMime")


class TestDeckBuilderNumber:
    def test_pokemon_filename(self):
        assert get_deck_builder_nr("cPK_10_000010_00_PIKACHU_C.png") == 1

    def test_trainer_filenames_are_offset(self):
        nr = get_deck_builder_nr("cTR_10_000010_00_POTION.png")
        assert nr == TRAINER_OFFSET + 1 and nr >= SPECIAL_THRESHOLD

    @pytest.mark.parametrize("filename", [
        "cPK_10_000011_00.png",   # does not end in 0
        "no_type_code_000010_.png",
        "",
        None,
    ])
    def test_unparsable_filenames_return_none(self, filename):
        assert get_deck_builder_nr(filename) is None


class TestDeckCode:
    def test_known_vectors(self):
        assert create_deck_code([1000001]) == "AZiWigA="
        assert create_deck_code([1, 2]) == "AAIAAAoAABQA"

    def test_binary_layout(self):
        """[trainers][count + 3-byte ids] then [pokemon] then [energy]."""
        decoded = base64.b64decode(create_deck_code([1000001, 5], [1, 2]))
        assert decoded == bytes([1, 0x98, 0x96, 0x8A, 1, 0, 0, 50, 2, 1, 2])

    def test_pokemon_numbers_are_stored_times_ten(self):
        decoded = base64.b64decode(create_deck_code([7]))
        assert decoded == bytes([0, 1, 0, 0, 70, 0])

    def test_trainer_numbers_are_stored_times_ten(self):
        """The game multiplies both segments; un-multiplied codes are rejected."""
        decoded = base64.b64decode(create_deck_code([1000001]))
        assert decoded[:4] == bytes([1]) + (1000001 * 10).to_bytes(3, "big")

    def test_cards_are_sorted_within_each_segment(self):
        assert create_deck_code([3, 1, 2]) == create_deck_code([1, 2, 3])
        assert create_deck_code([TRAINER_OFFSET + 3, TRAINER_OFFSET + 1]) == \
            create_deck_code([TRAINER_OFFSET + 1, TRAINER_OFFSET + 3])

    def test_energy_segment_is_omitted_for_a_trainer_only_deck(self):
        assert base64.b64decode(create_deck_code([1000001])) == \
            bytes([1]) + (1000001 * 10).to_bytes(3, "big") + bytes([0])

    def test_energy_ids_are_appended_as_single_bytes(self):
        with_energy = base64.b64decode(create_deck_code([1], [1, 3]))
        assert with_energy[-3:] == bytes([2, 1, 3])

    def test_energy_ids_are_appended_in_the_given_order(self):
        """The game rejected a deck whose ids arrived descending, so the
        encoder passes ids through untouched and callers sort first."""
        assert base64.b64decode(create_deck_code([2064], [2, 4]))[-2:] == bytes([2, 4])
        assert base64.b64decode(create_deck_code([2064], [4, 2]))[-2:] == bytes([4, 2])

    def test_game_generated_hoopa_greninja_deck(self):
        nrs = [
            2064, 2064, 87, 87, 89, 89, 1233,
            1000002, 1000003, 1000003, 1000048, 1000048, 1000128,
            1000152, 1000152, 1000004, 1000004, 1000032, 1000099, 1000099,
        ]
        assert create_deck_code(nrs, [7]) == (
            "DZiWlJiWnpiWnpiWqJiWqJiXwJiYYJiYYJiaXpiaXpibgJiccJiccAcA"
            "A2YAA2YAA3oAA3oAMCoAUKAAUKABBw=="
        )

    def test_empty_deck_is_none(self):
        assert create_deck_code([]) is None and create_deck_code(None) is None

    def test_negative_ids_are_rejected(self):
        with pytest.raises(ValueError):
            create_deck_code([-1])

    def test_ids_wider_than_three_bytes_are_rejected(self):
        with pytest.raises(ValueError):
            create_deck_code([0x1000000])

    def test_the_largest_pokemon_number_still_fits_in_three_bytes(self):
        """n * 10 for the largest non-special number is 999,990 < 0xFFFFFF."""
        decoded = base64.b64decode(create_deck_code([SPECIAL_THRESHOLD - 1]))
        assert decoded == bytes([0, 1, 0x0F, 0x42, 0x36, 0])

    def test_more_than_255_cards_in_a_segment_is_rejected(self):
        with pytest.raises(ValueError):
            create_deck_code(list(range(1, 258)))

    def test_more_than_255_trainers_in_a_segment_is_rejected(self):
        with pytest.raises(ValueError):
            create_deck_code(list(range(TRAINER_OFFSET, TRAINER_OFFSET + 258)))

    def test_more_than_255_energies_is_rejected(self):
        with pytest.raises(ValueError):
            create_deck_code([1], [1] * 256)
