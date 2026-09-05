"""The writer adapters own the mode split; the orchestrator picks one."""
from unittest.mock import patch

import pytest

import set_writer
from constants import EXPANSIONS_JSON_PATH
from set_writer import V4Writer, V5Writer, writer_for


def test_writer_for_rejects_unknown_modes():
    with pytest.raises(ValueError, match="mode"):
        writer_for("v6", "a1", "Genetic Apex")


def test_writer_for_rejects_empty_string():
    with pytest.raises(ValueError, match="mode"):
        writer_for("", "a1", "Genetic Apex")


@pytest.mark.parametrize("mode, cls", [("v4", V4Writer), ("v5", V5Writer)])
def test_writer_for_returns_the_right_adapter(mode, cls):
    assert isinstance(writer_for(mode, "a1", "Genetic Apex"), cls)


class TestV4Writer:
    def test_downgrades_validates_and_appends(self):
        w = V4Writer()
        with patch("set_writer.downgrade_to_v4", return_value=[{"id": "a1-001"}]) as dg, \
             patch("set_writer.validate_schema") as vs, \
             patch("set_writer.append_to_v4", return_value=3) as ap:
            added, packs = w.write([{"id": "a1-001", "source_url": "x"}])
        dg.assert_called_once_with([{"id": "a1-001", "source_url": "x"}])
        vs.assert_called_once_with([{"id": "a1-001"}], set_writer.V4_CARDS_SCHEMA_PATH, "v4 cards")
        ap.assert_called_once_with([{"id": "a1-001"}])
        assert (added, packs) == (3, None)


class TestV5Writer:
    def test_validates_writes_updates_and_validates_the_index(self):
        w = V5Writer("a1", "Genetic Apex")
        cards = [{"id": "a1-001"}]
        with patch("set_writer.validate_schema") as vs, \
             patch("set_writer.write_set_file", return_value=2) as wsf, \
             patch("set_writer.update_expansions", return_value=["Mewtwo"]) as ue, \
             patch("set_writer._load_existing_json", return_value=[{"id": "a1"}]) as le:
            added, packs = w.write(cards)
        assert vs.call_count == 2
        wsf.assert_called_once_with(cards)
        ue.assert_called_once_with("a1", "Genetic Apex", cards)
        le.assert_called_once_with(EXPANSIONS_JSON_PATH)
        assert (added, packs) == (2, ["Mewtwo"])

    def test_validates_cards_before_writing(self):
        """Schema check runs first so a broken batch never reaches disk."""
        w = V5Writer("a1", "Genetic Apex")
        cards = [{"id": "a1-001"}]
        order = []

        def fake_validate(instance, schema_path=None, label="cards"):
            order.append(("validate", label))

        def fake_write(cards):
            order.append(("write", None))
            return 1

        with patch("set_writer.validate_schema", side_effect=fake_validate), \
             patch("set_writer.write_set_file", side_effect=fake_write), \
             patch("set_writer.update_expansions", return_value=["Mewtwo"]), \
             patch("set_writer._load_existing_json", return_value=[]):
            w.write(cards)
        assert order[0] == ("validate", "cards")
        assert order[-1] == ("validate", "expansions")