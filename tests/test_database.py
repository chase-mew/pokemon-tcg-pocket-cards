"""Unit tests for the JSON persistence layer.

Every test redirects the module-level paths in ``database`` at a tmp_path, so
nothing here touches the committed dataset.
"""
import json

import pytest

import database
from database import (_card_number, _set_sort_key, append_to_v4, build_expansion_entry,
                      compile_v5_database, minified_path, write_json_pair, read_all_v5_cards,
                      sync_alternate_versions, update_expansions, write_set_file)


def card(card_id, **overrides):
    prefix, number = card_id.rsplit("-", 1)
    data = {
        "id": card_id,
        "set_code": prefix,
        "set_name": "Genetic Apex",
        "pack": "Mewtwo",
        "release_date": "2024-10-30",
        "type": "Pokémon",
        "rarity": "◊",
        "alternate_versions": [],
    }
    data.update(overrides)
    return data


def read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def v5_dir(tmp_path, monkeypatch):
    """Point database.py at an empty tmp data tree."""
    root = tmp_path / "v5"
    root.mkdir()
    monkeypatch.setattr(database, "V5_DIR", str(root))
    monkeypatch.setattr(database, "CARDS_JSON_PATH", str(root / "cards.json"))
    monkeypatch.setattr(database, "V5_CORE_CARDS_PATH", str(root / "cards.core.json"))
    monkeypatch.setattr(database, "V5_CORE_NO_IMAGE_CARDS_PATH", str(root / "cards.core.no-image.json"))
    monkeypatch.setattr(database, "V5_GAMEPLAY_CARDS_PATH", str(root / "cards.gameplay.json"))
    monkeypatch.setattr(database, "EXPANSIONS_JSON_PATH", str(root / "expansions.json"))
    monkeypatch.setattr(database, "V4_JSON_PATH", str(tmp_path / "v4" / "cards.json"))
    return root


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

class TestWriteJsonPair:
    def test_writes_both_files_with_the_same_content(self, tmp_path):
        path = tmp_path / "a1.json"
        write_json_pair([{"id": "a1-001"}], str(path))
        assert read(path) == read(minified_path(str(path)))

    def test_pretty_file_is_indented_and_minified_file_is_not(self, tmp_path):
        path = tmp_path / "a1.json"
        write_json_pair([{"id": "a1-001"}], str(path))
        assert "\n  " in path.read_text(encoding="utf-8")
        assert ", " not in (tmp_path / "a1.min.json").read_text(encoding="utf-8")

    def test_line_endings_are_lf_on_every_platform(self, tmp_path):
        path = tmp_path / "a1.json"
        write_json_pair([{"id": "a1-001"}, {"id": "a1-002"}], str(path))
        assert b"\r\n" not in path.read_bytes()

    def test_non_ascii_survives_the_round_trip(self, tmp_path):
        path = tmp_path / "a1.json"
        write_json_pair([{"rarity": "◊◊", "type": "Pokémon"}], str(path))
        assert "◊◊" in path.read_text(encoding="utf-8")
        assert read(path)[0]["type"] == "Pokémon"

    def test_minified_path_swaps_the_suffix_only(self):
        assert minified_path("/data/v5.json/a1.json") == "/data/v5.json/a1.min.json"


class TestSortKeys:
    def test_sets_sort_in_release_order_past_nine(self):
        codes = ["b10", "b1", "b2a", "b1a", "a1", "pa"]
        assert sorted(codes, key=_set_sort_key) == ["a1", "b1", "b1a", "b2a", "b10", "pa"]

    def test_card_numbers_sort_numerically(self):
        cards = [card("a1-010"), card("a1-002"), card("a1-100")]
        assert [c["id"] for c in sorted(cards, key=_card_number)] == [
            "a1-002", "a1-010", "a1-100"]


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------

class TestWriteSetFile:
    def test_writes_a_per_set_file_and_counts_new_cards(self, v5_dir):
        added = write_set_file([card("a1-001"), card("a1-002")])
        assert added == 2
        assert len(read(v5_dir / "a1" / "a1.json")) == 2

    def test_existing_ids_are_overwritten_not_duplicated(self, v5_dir):
        write_set_file([card("a1-001", name="old")])
        added = write_set_file([card("a1-001", name="new"), card("a1-002")])
        assert added == 1
        saved = read(v5_dir / "a1" / "a1.json")
        assert len(saved) == 2
        assert saved[0]["name"] == "new"

    def test_merged_set_is_sorted_by_card_number(self, v5_dir):
        write_set_file([card("a1-010")])
        write_set_file([card("a1-002"), card("a1-100")])
        assert [c["id"] for c in read(v5_dir / "a1" / "a1.json")] == \
               ["a1-002", "a1-010", "a1-100"]

    def test_minified_sibling_is_written_too(self, v5_dir):
        write_set_file([card("a1-001")])
        assert (v5_dir / "a1" / "a1.min.json").exists()


class TestAppendToV4:
    def test_v4_goes_to_the_single_legacy_file(self, v5_dir, tmp_path):
        append_to_v4([{"id": "a1-001", "type": "Trainer"}])
        added = append_to_v4([{"id": "a1-001", "type": "Item"}, {"id": "a1-002"}])
        assert added == 1


class TestSyncAlternateVersions:
    def test_reference_becomes_bidirectional(self):
        a = card("a1-001", alternate_versions=[
            {"set_code": "a2", "set_name": "Space-Time Smackdown", "id": 5, "rarity": "☆"}])
        b = card("a2-005", set_name="Space-Time Smackdown", rarity="☆")
        sync_alternate_versions([a, b])
        assert [alt["set_code"] for alt in b["alternate_versions"]] == ["a1"]
        assert [alt["id"] for alt in a["alternate_versions"]] == [5]

    def test_a_card_never_lists_itself(self):
        a = card("a1-001", alternate_versions=[
            {"set_code": "a1", "set_name": "Genetic Apex", "id": 1, "rarity": "◊"},
            {"set_code": "a1", "set_name": "Genetic Apex", "id": 2, "rarity": "☆"}])
        b = card("a1-002", rarity="☆")
        sync_alternate_versions([a, b])
        assert [alt["id"] for alt in a["alternate_versions"]] == [2]

    def test_transitive_groups_are_fully_connected(self):
        a = card("a1-001", alternate_versions=[
            {"set_code": "a1", "set_name": "Genetic Apex", "id": 2, "rarity": "☆"}])
        b = card("a1-002", rarity="☆", alternate_versions=[
            {"set_code": "a1", "set_name": "Genetic Apex", "id": 3, "rarity": "☆☆"}])
        c = card("a1-003", rarity="☆☆")
        sync_alternate_versions([a, b, c])
        assert [alt["id"] for alt in a["alternate_versions"]] == [2, 3]
        assert [alt["id"] for alt in c["alternate_versions"]] == [1, 2]

    def test_alternates_are_sorted_by_set_then_number(self):
        a = card("a1-001", alternate_versions=[
            {"set_code": "b1", "set_name": "Mega Rising", "id": 9, "rarity": "◊"},
            {"set_code": "a2", "set_name": "Space-Time Smackdown", "id": 7, "rarity": "◊"}])
        others = [card("b1-009", set_name="Mega Rising"),
                  card("a2-007", set_name="Space-Time Smackdown")]
        sync_alternate_versions([a, *others])
        assert [(alt["set_code"], alt["id"]) for alt in a["alternate_versions"]] == [
            ("a2", 7), ("b1", 9)]

    def test_unknown_references_are_dropped(self):
        a = card("a1-001", alternate_versions=[
            {"set_code": "zz", "set_name": "Not Scraped Yet", "id": 1, "rarity": "◊"}])
        sync_alternate_versions([a])
        assert a["alternate_versions"] == []

    def test_null_rarity_is_reported_as_promo(self):
        a = card("a1-001", alternate_versions=[
            {"set_code": "pa", "set_name": "Promo-A", "id": 3, "rarity": "Promo"}])
        b = card("pa-003", set_name="Promo-A", rarity=None)
        sync_alternate_versions([a, b])
        assert a["alternate_versions"][0]["rarity"] == "Promo"


# ---------------------------------------------------------------------------
# Expansions index
# ---------------------------------------------------------------------------

class TestBuildExpansionEntry:
    def test_is_pure(self, v5_dir):
        """No file is touched; the caller decides when to write."""
        before = (v5_dir / "expansions.json").exists()
        entry = build_expansion_entry("a1", "Genetic Apex", [card("a1-001", pack="Charizard")])
        assert entry["id"] == "a1"
        assert entry["total_cards"] == 1
        assert (v5_dir / "expansions.json").exists() is before


class TestUpdateExpansions:
    def test_named_packs_become_pack_entries(self, v5_dir):
        packs = update_expansions("A1", "Genetic Apex", [
            card("a1-001", pack="Mewtwo"), card("a1-002", pack="Charizard"),
            card("a1-003", pack="Shared(Genetic Apex)")])
        assert [(p["id"], p["name"]) for p in packs] == [
            ("a1-charizard", "Charizard"), ("a1-mewtwo", "Mewtwo")]

    def test_a_set_with_no_named_packs_gets_a_single_booster(self, v5_dir):
        packs = update_expansions("B3b", "Everyday Wonders",
                                  [card("b3b-001", pack="Everyday Wonders")])
        assert [p["id"] for p in packs] == ["b3b-booster"]

    def test_pack_images_point_at_the_slugged_id(self, v5_dir):
        packs = update_expansions("A1", "Genetic Apex", [card("a1-001", pack="Mewtwo")])
        assert packs[0]["image"].endswith("/webp/packs/a1-mewtwo.webp")
        assert packs[0]["image_png"].endswith("/png/packs/a1-mewtwo.png")

    def test_promo_packs_have_no_images(self, v5_dir):
        packs = update_expansions("P-A", "Promo-A", [card("pa-001", pack="Promo V1")])
        assert packs[0]["image"] is None and packs[0]["image_png"] is None

    def test_release_date_is_the_earliest_non_null(self, v5_dir):
        update_expansions("A1", "Genetic Apex", [
            card("a1-001", release_date=None),
            card("a1-002", release_date="2024-10-30"),
            card("a1-003", release_date="2025-01-01")])
        assert read(v5_dir / "expansions.json")[0]["release_date"] == "2024-10-30"

    def test_release_date_is_null_when_no_card_has_one(self, v5_dir):
        update_expansions("P-A", "Promo-A", [card("pa-001", release_date=None)])
        assert read(v5_dir / "expansions.json")[0]["release_date"] is None

    def test_entry_is_updated_in_place_not_duplicated(self, v5_dir):
        update_expansions("A1", "Genetic Apex", [card("a1-001")])
        update_expansions("A1", "Genetic Apex", [card("a1-001"), card("a1-002")])
        stored = read(v5_dir / "expansions.json")
        assert len(stored) == 1 and stored[0]["total_cards"] == 2

    def test_urls_match_the_on_disk_layout(self, v5_dir):
        update_expansions("A1", "Genetic Apex", [card("a1-001")])
        entry = read(v5_dir / "expansions.json")[0]
        assert entry["cards_url"].endswith("/data/v5/a1/a1.json")
        assert entry["cards_url_min"].endswith("/data/v5/a1/a1.min.json")


# ---------------------------------------------------------------------------
# Full compile
# ---------------------------------------------------------------------------

@pytest.fixture
def populated(v5_dir):
    write_set_file([card("a1-002"), card("a1-001", alternate_versions=[
        {"set_code": "b10", "set_name": "Future Set", "id": 3, "rarity": "☆"}])])
    write_set_file([card("b10-003", set_code="b10", set_name="Future Set", rarity="☆")])
    write_set_file([card("b2-001", set_code="b2", set_name="Deluxe", rarity="◊")])
    return v5_dir


class TestCompileV5Database:
    def test_reads_every_set_directory(self, populated):
        assert len(read_all_v5_cards()) == 4

    def test_master_file_is_sorted_by_set_then_number(self, populated):
        compile_v5_database()
        assert [c["id"] for c in read(populated / "cards.json")] == [
            "a1-001", "a1-002", "b2-001", "b10-003"]

    def test_alternate_versions_are_synced_across_sets(self, populated):
        compile_v5_database()
        by_id = {c["id"]: c for c in read(populated / "cards.json")}
        assert by_id["b10-003"]["alternate_versions"][0]["set_code"] == "a1"

    def test_every_set_gets_an_expansion_entry(self, populated):
        compile_v5_database()
        assert {e["id"] for e in read(populated / "expansions.json")} == {"a1", "b2", "b10"}

    def test_per_set_files_stay_in_sync_with_the_master_file(self, populated):
        compile_v5_database()
        master = read(populated / "cards.json")
        from_sets = [c for prefix in ("a1", "b2", "b10")
                     for c in read(populated / prefix / f"{prefix}.json")]
        assert sorted(c["id"] for c in master) == sorted(c["id"] for c in from_sets)

    def test_minified_master_matches(self, populated):
        compile_v5_database()
        assert read(populated / "cards.json") == read(populated / "cards.min.json")

    def test_compiling_twice_changes_nothing(self, populated):
        compile_v5_database()
        first = (populated / "cards.json").read_bytes()
        compile_v5_database()
        assert (populated / "cards.json").read_bytes() == first

    def test_empty_data_dir_is_not_an_error(self, v5_dir):
        compile_v5_database()
        assert read(v5_dir / "cards.json") == []


class TestCompileWritesTheIndexOnce:
    def test_index_is_written_a_single_time(self, populated, monkeypatch):
        writes = []
        original = database.write_json_pair
        monkeypatch.setattr(database, "write_json_pair",
                            lambda d, p: (writes.append(p), original(d, p))[1])
        database.compile_v5_database()
        index_writes = [p for p in writes if p.endswith("expansions.json")]
        assert len(index_writes) == 1, f"index rewritten {len(index_writes)}x"
