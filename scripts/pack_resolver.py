# Copyright (C) 2024 Chase Manning <chase@manning.dev>
# Copyright (C) 2026 Leonid Dalin <infoLeonid@protonmail.com> & Chase Manning <chase@manning.dev>
#
# Original code by Chase Manning is released under the MIT License.
# Modifications and additions for version 5 onwards are released under
# the GNU Affero General Public License v3.0 (AGPL-3.0-or-later).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
r"""Resolve a card's published pack name from its scraped pack value.

Promo-A groups its cards into numbered volumes of
:data:`constants.PROMO_CARDS_PER_VOLUME`, which is only knowable from the
cards seen before this one, so this is an object with state rather than a
pure function. Create one per set and call :meth:`resolve` once per card in
printed order.
"""

from constants import PROMO_CARDS_PER_VOLUME


class PackResolver:
    r"""Maps a scraped pack value onto the published one for a set."""

    def __init__(self, set_profile, expansion_name, specific_packs):
        self._set = set_profile
        self._expansion_name = expansion_name
        self._specific_packs = specific_packs
        self._volume = 1
        self._volume_count = 0

    def resolve(self, card):
        r"""resolve(card) -> str

        Args:
            card (dict): a raw scraped card. Reads ``pack`` only.

        Returns:
            str: the published pack name.
        """
        pack = card["pack"]
        if self._set.is_promo_a:
            return self._promo_a(pack)
        if self._set.is_promo:
            return self._expansion_name
        if pack == "Every pack":
            return f"Shared({self._expansion_name})" if self._specific_packs else self._expansion_name
        if pack.endswith(" pack"):
            return pack[:-5].strip()
        return pack

    def _promo_a(self, pack):
        if pack == "Promo pack":
            self._volume_count += 1
            if self._volume_count > PROMO_CARDS_PER_VOLUME:
                self._volume, self._volume_count = self._volume + 1, 1
            return f"Promo V{self._volume}"
        if pack == "Every pack":
            return self._expansion_name
        return pack
