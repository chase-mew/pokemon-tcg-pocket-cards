"""Unit tests for pack resolution, exercised without the full transform."""
from pack_resolver import PackResolver
from set_profile import SetProfile


def card(pack):
    return {"pack": pack}


def resolve_all(set_code, expansion_name, packs, specific=frozenset()):
    r = PackResolver(SetProfile.of(set_code), expansion_name, specific)
    return [r.resolve(card(p)) for p in packs]


class TestRegularSets:
    def test_pack_suffix_is_stripped(self):
        assert resolve_all("A1", "Genetic Apex", ["Mewtwo pack"]) == ["Mewtwo"]

    def test_every_pack_becomes_shared_when_named_packs_exist(self):
        assert resolve_all("A1", "Genetic Apex", ["Every pack"], {"Mewtwo pack"}) == \
               ["Shared(Genetic Apex)"]

    def test_every_pack_becomes_the_expansion_when_it_is_the_only_pack(self):
        assert resolve_all("B3b", "Everyday Wonders", ["Every pack"]) == ["Everyday Wonders"]


class TestPromo:
    def test_promo_a_groups_promo_packs_into_volumes_of_five(self):
        got = resolve_all("P-A", "Promo-A", ["Promo pack"] * 11)
        assert got[:5] == ["Promo V1"] * 5
        assert got[5:10] == ["Promo V2"] * 5
        assert got[10] == "Promo V3"

    def test_promo_a_keeps_named_promo_packs(self):
        assert resolve_all("P-A", "Promo-A", ["Premium Missions", "Shop"]) == \
               ["Premium Missions", "Shop"]

    def test_promo_b_cards_land_on_the_expansion_name(self):
        assert resolve_all("P-B", "Promo-B", ["Every pack"]) == ["Promo-B"]
