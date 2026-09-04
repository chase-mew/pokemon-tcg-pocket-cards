"""Unit tests for the art-style state machine, exercised without the transform."""
from art_style import ArtStyleClassifier


def card(rarity, type="Pokémon", ex=False, mega=False, raw_text=""):
    return {"rarity": rarity, "type": type, "ex": ex, "mega": mega, "raw_text": raw_text}


def styles(*cards):
    c = ArtStyleClassifier()
    return [c.classify(x)[0] for x in cards]


class TestBlocks:
    def test_plain_star_is_illustration_art(self):
        assert styles(card("◊"), card("☆")) == [None, "Illustration Art"]

    def test_star_run_then_two_star_is_full_art(self):
        assert styles(card("☆"), card("☆☆")) == ["Illustration Art", "Full Art"]

    def test_sia_starts_after_the_trainer_full_art(self):
        assert styles(card("☆"), card("☆☆", type="Trainer"), card("☆☆", ex=True)) == \
               ["Illustration Art", "Full Art", "Special Illustration Art"]

    def test_three_star_is_immersive(self):
        assert styles(card("☆☆☆")) == ["Immersive Art"]

    def test_crown_rare_stays_unclassified(self):
        assert styles(card("Crown Rare")) == [None]


class TestShiny:
    def test_star_after_immersive_is_shiny(self):
        c = ArtStyleClassifier()
        c.classify(card("☆☆☆"))
        assert c.classify(card("☆")) == ("Shiny", True)

    def test_two_star_after_immersive_is_shiny_full_art(self):
        c = ArtStyleClassifier()
        c.classify(card("☆☆☆"))
        assert c.classify(card("☆☆")) == ("Shiny Full Art", True)

    def test_trainer_in_the_shiny_block_is_neither(self):
        c = ArtStyleClassifier()
        c.classify(card("☆☆☆"))
        assert c.classify(card("☆", type="Trainer")) == (None, False)


class TestParallelFoil:
    def test_identical_raw_text_on_a_diamond_rarity(self):
        assert styles(card("◊", raw_text="Pikachu"), card("◊", raw_text="Pikachu")) == \
               [None, "Parallel Foil"]

    def test_star_rarities_are_not_parallel_foils(self):
        assert styles(card("☆", raw_text="P"), card("☆", raw_text="P")) == \
               ["Illustration Art", "Illustration Art"]
