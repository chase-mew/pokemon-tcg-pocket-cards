import re
from collections import defaultdict


PROMO_EXPANSION_ID = "promo"
PROMO_CARD_PREFIXES = {"pa", "pb"}


def get_card_prefix(card_id):
    return card_id.rsplit("-", 1)[0]


class TestCardExpansionMapping:
    def test_every_card_prefix_has_expansion(self, cards, expansions):
        """Every card ID prefix should map to an expansion in expansions.json."""
        exp_ids = {e["id"] for e in expansions}
        exp_ids_with_promos = exp_ids | PROMO_CARD_PREFIXES

        card_prefixes = {get_card_prefix(c["id"]) for c in cards}
        unmapped = card_prefixes - exp_ids_with_promos
        assert not unmapped, (
            f"Card prefixes with no matching expansion: {unmapped}"
        )

    def test_every_expansion_has_cards(self, cards, expansions):
        """Every expansion should have at least one card in v4.json."""
        card_prefixes = {get_card_prefix(c["id"]) for c in cards}
        card_prefixes_with_promo = card_prefixes | {PROMO_EXPANSION_ID}

        for exp in expansions:
            if exp["id"] == PROMO_EXPANSION_ID:
                has_cards = bool(PROMO_CARD_PREFIXES & card_prefixes)
            else:
                has_cards = exp["id"] in card_prefixes_with_promo
            assert has_cards, (
                f"Expansion '{exp['id']}' ({exp['name']}) has no cards in v4.json"
            )


class TestPackConsistency:
    def test_non_promo_cards_have_recognizable_pack(self, cards, expansions):
        """Non-promo card pack values should relate to expansion names or pack names."""
        exp_names = {e["name"] for e in expansions}
        pack_names = set()
        for e in expansions:
            for p in e["packs"]:
                pack_names.add(p["name"])

        valid_pack_names = exp_names | pack_names

        for card in cards:
            prefix = get_card_prefix(card["id"])
            if prefix in PROMO_CARD_PREFIXES:
                continue

            pack = card["pack"]
            if pack.startswith("Shared(") and pack.endswith(")"):
                inner = pack[7:-1]
                assert inner in exp_names, (
                    f"Card {card['id']} has Shared pack referencing unknown expansion: '{inner}'"
                )
                continue

            assert pack in valid_pack_names, (
                f"Card {card['id']} has pack '{pack}' which doesn't match any expansion or pack name"
            )


class TestCardOrdering:
    def test_cards_grouped_by_expansion(self, cards):
        """Non-promo cards should be grouped by expansion prefix (not interleaved).

        Promo sets (pa, pb) are excluded because new promos are added
        incrementally over time, so they naturally appear in multiple blocks.
        """
        seen_prefixes = []
        current_prefix = None

        for card in cards:
            prefix = get_card_prefix(card["id"])
            if prefix in PROMO_CARD_PREFIXES:
                continue
            if prefix != current_prefix:
                assert prefix not in seen_prefixes, (
                    f"Expansion prefix '{prefix}' appears in multiple non-contiguous "
                    f"blocks. Cards should be grouped by expansion."
                )
                seen_prefixes.append(prefix)
                current_prefix = prefix


class TestCardCounts:
    def test_minimum_total_cards(self, cards):
        assert len(cards) >= 500, (
            f"Expected at least 500 cards, got {len(cards)}"
        )

    def test_minimum_expansions(self, expansions):
        assert len(expansions) >= 5, (
            f"Expected at least 5 expansions, got {len(expansions)}"
        )

    def test_each_expansion_has_reasonable_card_count(self, cards, expansions):
        """Each non-promo expansion should have at least a few cards."""
        prefix_counts = defaultdict(int)
        for card in cards:
            prefix_counts[get_card_prefix(card["id"])] += 1

        for exp in expansions:
            if exp["id"] == PROMO_EXPANSION_ID:
                total = sum(prefix_counts.get(p, 0) for p in PROMO_CARD_PREFIXES)
            else:
                total = prefix_counts.get(exp["id"], 0)
            assert total >= 5, (
                f"Expansion '{exp['id']}' ({exp['name']}) has only {total} cards"
            )
