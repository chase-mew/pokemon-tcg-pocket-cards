# QR encoding logic ported from [Nirostar/ptcgp-deck-qr/](https://github.com/Nirostar/ptcgp-deck-qr) (MIT License) @ 2026 Nirostar
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
r"""Encode card numbers into the base64 format used by the in-game
deck builder.

The encoding logic was ported from Nirostar's ptcgp-deck-qr project
(MIT Licence). Each card has a deck-builder number: a small integer
for Pokemon cards, and the same integer plus a large offset for
trainer cards. These numbers are packed into a binary format and
base64-encoded to produce the share codes seen in the game.
"""

import base64
import re

TRAINER_OFFSET = 1_000_000  # Added to trainer card numbers to distinguish them from Pokemon
SPECIAL_THRESHOLD = 100_000  # Numbers at or above this are "special" (trainer) cards in the encoding


def get_deck_builder_nr(image_filename):
    r"""get_deck_builder_nr(image_filename) -> int or None

    Parse a deck-builder number from an image filename in the
    Flibustier's datamine database. The filename contains a card type
    code (uppercase letters) and a 6-digit number. The 6-digit number
    must end in 0 to be valid; the deck-builder number is that value
    divided by 10.

    Trainer cards have the type code ``"TR"`` and get
    ``TRAINER_OFFSET`` added to their number so they fall above
    ``SPECIAL_THRESHOLD`` in the encoding.

    Args:
        image_filename (str or None): the image filename to parse.
            Expected format: ``c{TYPE}_{digits}_{6-digit-number}_``
            where ``{TYPE}`` is uppercase letters.

    Returns:
        int or None: the deck-builder number, or ``None`` if the
        filename does not match the expected pattern or the 6-digit
        number does not end in 0

    Example::

        >>> get_deck_builder_nr("cPKMN_001_000100_img.png")
        10
        >>> get_deck_builder_nr("cTR_001_000200_img.png")
        1000020
        >>> get_deck_builder_nr(None)
        None
        >>> get_deck_builder_nr("invalid")
        None
    """
    match = re.search(r"c([A-Z]+)_\d+_(\d{6})_", str(image_filename or ""))
    if not match or int(match.group(2)) % 10 != 0: return None
    nr = int(match.group(2)) // 10
    return TRAINER_OFFSET + nr if match.group(1) == "TR" else nr


def create_deck_code(nrs, energy_ids=None):
    r"""create_deck_code(nrs, energy_ids=None) -> str or None

    Encode a list of deck-builder numbers into the base64 deck code
    used by the in-game deck builder. This is the general version
    that handles full decks; :func:`create_single_card_code` wraps it
    for single-card codes.

    The binary format has three sections, written sequentially:

    1. **Special cards** (trainers, numbers at or above
       ``SPECIAL_THRESHOLD``): 1-byte count, then one 3-byte
       big-endian integer per card. Each value is the card number
       multiplied by 10.
    2. **Normal cards** (Pokemon, numbers below
       ``SPECIAL_THRESHOLD``): same layout as special cards.
    3. **Energy IDs**: 1-byte count, then one byte per energy ID.

    The entire byte array is base64-encoded with standard padding.
    Card numbers within each section are sorted before encoding.

    Args:
        nrs (list of int): deck-builder numbers, as returned by
            :func:`get_deck_builder_nr`. Can be empty, in which case
            ``None`` is returned.
        energy_ids (list of int or None): optional energy card IDs
            to append to the code. Each ID is written as a single
            byte. Default: ``None`` (treated as an empty list)

    Returns:
        str or None: base64-encoded deck code, or ``None`` if
        ``nrs`` is empty

    Raises:
        ValueError: if any card number multiplied by 10 exceeds
            3 bytes (``0xFFFFFF`` = 16,777,215)

    Example::

        >>> create_deck_code([10, 20])
        'AAIAAGQAAMgA'
        >>> create_deck_code([10])
        'AAEAAGQA'
        >>> create_deck_code([])
        None
    """
    if not nrs: return None
    specials, normals = sorted(n for n in nrs if n >= SPECIAL_THRESHOLD), sorted(
        n for n in nrs if n < SPECIAL_THRESHOLD)
    b = bytearray()

    for group in (specials, normals):
        b.append(len(group) & 0xff)
        for n in group:
            v = n * 10
            if v > 0xFFFFFF: raise ValueError("ID exceeds 3 bytes")
            b.extend([(v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff])

    energy_ids = energy_ids or []
    b.extend([len(energy_ids) & 0xff, *energy_ids])
    return base64.b64encode(b).decode("utf-8")


def create_single_card_code(nr):
    r"""create_single_card_code(nr) -> str or None

    Encode a single card's deck-builder number into a base64 share
    code. This is a thin wrapper around :func:`create_deck_code`
    that passes the number as a one-element list.

    Args:
        nr (int): the deck-builder number, as returned by
            :func:`get_deck_builder_nr`

    Returns:
        str or None: base64 share code, or ``None`` if ``nr`` is
        not a positive integer

    Raises:
        ValueError: if the card number multiplied by 10 exceeds
            3 bytes (``0xFFFFFF`` = 16,777,215)

    Example::

        >>> create_single_card_code(10)
        'AAEAAGQA'
        >>> create_single_card_code(1000020)
        'AZiXSAAA'
        >>> create_single_card_code(0)
        None
        >>> create_single_card_code(None)
        None
    """
    return create_deck_code([nr]) if isinstance(nr, int) and nr > 0 else None