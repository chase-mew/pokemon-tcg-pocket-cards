"""One place decides what a set code means."""
import pytest
from set_profile import SetProfile


class TestOf:
    @pytest.mark.parametrize("raw, code, prefix", [
        ("a1", "A1", "a1"), ("A1", "A1", "a1"), ("b2b", "B2B", "b2b"),
        ("pa", "P-A", "pa"), ("PA", "P-A", "pa"), ("P-A", "P-A", "pa"),
        ("pb", "P-B", "pb"),
    ])
    def test_normalises_both_representations(self, raw, code, prefix):
        p = SetProfile.of(raw)
        assert (p.code, p.prefix) == (code, prefix)

    @pytest.mark.parametrize("raw, promo, promo_a", [
        ("a1", False, False), ("pa", True, True), ("PA", True, True), ("pb", True, False),
    ])
    def test_promo_flags(self, raw, promo, promo_a):
        p = SetProfile.of(raw)
        assert (p.is_promo, p.is_promo_a) == (promo, promo_a)

    def test_is_idempotent(self):
        assert SetProfile.of(SetProfile.of("pa").code) == SetProfile.of("pa")
