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
r"""Classify a card's art style and shiny flag from its position in a set.

The website prints a set's special art in fixed blocks: the one-star
Illustration Art run, then the two-star Full Art run, then the Special
Illustration Art run, then the single three-star Immersive card, after
which further one- and two-star cards are shiny reprints. Which block a
card sits in is only knowable from the cards printed before it, which is
why this is an object with state rather than a pure function.
"""

from constants import PARALLEL_FOIL_RARITIES


class ArtStyleClassifier:
    r"""Assigns ``(art_style, shiny)`` to a set's cards.

    Create one instance per set and call :meth:`classify` once per card, in
    printed (ascending card-number) order. Reordering, filtering or
    reusing an instance across sets misclassifies the blocks.
    """

    def __init__(self):
        self._seen_three_star = False
        self._seen_trainer_full_art = False
        self._in_full_art = False
        self._in_sia = False
        self._prev_rarity = ""
        self._prev_raw_text = ""

    def classify(self, card):
        r"""classify(card) -> (art_style, shiny)

        Args:
            card (dict): a raw scraped card. Reads ``rarity``, ``type``,
                ``ex``, ``mega`` and ``raw_text``.

        Returns:
            tuple: ``(art_style, shiny)``. art_style is one of
            :data:`constants.ART_STYLES` or None; shiny is a bool.
        """
        rarity, raw_text = card["rarity"], card.get("raw_text", "")
        art_style, shiny = self._by_rarity(card, rarity)

        # A parallel foil reprints the card body verbatim at the same rarity.
        if raw_text and raw_text == self._prev_raw_text and rarity in PARALLEL_FOIL_RARITIES:
            art_style = "Parallel Foil"

        # Trainers appear inside the shiny block but are never shiny.
        if card["type"] == "Trainer" and art_style in ("Shiny", "Shiny Full Art"):
            art_style, shiny = None, False

        self._prev_rarity, self._prev_raw_text = rarity, raw_text
        return art_style, shiny

    def _by_rarity(self, card, rarity):
        if rarity == "☆☆☆":
            self._seen_three_star = True
            return "Immersive Art", False
        if self._seen_three_star and rarity == "☆":
            return "Shiny", True
        if self._seen_three_star and rarity == "☆☆":
            return "Shiny Full Art", True
        if rarity == "☆" and not (card["mega"] or card["ex"]):
            return "Illustration Art", False
        if rarity == "☆☆":
            return self._two_star(card), False
        return None, False

    def _two_star(self, card):
        # The Full Art run opens at the ☆ -> ☆☆ boundary and closes when
        # the first ex/mega after a trainer Full Art starts the SIA run.
        if self._prev_rarity == "☆" and not self._in_sia:
            self._in_full_art = True
        if self._in_full_art and self._seen_trainer_full_art and (card["mega"] or card["ex"]):
            self._in_full_art, self._in_sia = False, True
        if not (self._in_sia or self._in_full_art):
            self._in_full_art = True
        if self._in_sia:
            return "Special Illustration Art"
        if card["type"] == "Trainer":
            self._seen_trainer_full_art = True
        return "Full Art"
