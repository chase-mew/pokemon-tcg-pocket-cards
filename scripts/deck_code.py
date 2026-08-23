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
r"""Encode card numbers into the base64 deck-code format used by the
in-game deck builder.

Each card has a deck-builder number: a small integer for Pokemon
cards, and the same integer plus a large offset for trainer cards.
These numbers are packed into a binary format and base64-encoded to
produce the share codes seen in the game.
"""

import base64
import re

TRAINER_OFFSET = 1_000_000  # Added to trainer card numbers to distinguish them from Pokemon
SPECIAL_THRESHOLD = 100_000  # Numbers at or above this are "special" (trainer) cards in the encoding


def get_deck_builder_nr(image_filename):
    r"""get_deck_builder_nr(image_filename) -> int or None

    Parse a deck-builder number from an image filename in the
    Flibustier datamine database. The filename contains a card type
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
    """
    match = re.search(r"c([A-Z]+)_\d+_(\d{6})_", str(image_filename or ""))
    if not match:
        return None
    raw = int(match.group(2))
    if raw % 10 != 0:
        return None
    nr = raw // 10
    return TRAINER_OFFSET + nr if match.group(1) == "TR" else nr


def create_deck_code(nrs, energy_ids=None):
    r"""create_deck_code(nrs, energy_ids=None) -> str or None

    Encode a list of deck-builder numbers into the base64 deck code
    used by the in-game deck builder.

    The binary format has three sections, written sequentially:

    1. **Trainer segment** (numbers at or above
       ``SPECIAL_THRESHOLD``): 1-byte count, then one 3-byte
       big-endian integer per card. Values are written as
       ``nr * 10``, matching the Pokémon segment.
    2. **Pokemon segment** (numbers below
       ``SPECIAL_THRESHOLD``): 1-byte count, then one 3-byte
       big-endian integer per card. Each value is the card number
       multiplied by 10.
    3. **Energy segment**: 1-byte count, then one byte per energy
       ID. This segment is omitted entirely when both the Pokemon
       segment and ``energy_ids`` are empty.

    Card numbers within each section are sorted before encoding.
    The entire byte array is base64-encoded with standard padding.

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
        ValueError: if any trainer card number exceeds 3 bytes
            (``0xFFFFFF`` = 16,777,215), if any Pokemon number
            multiplied by 10 exceeds 3 bytes, or if any segment
            has more than 255 entries
    """
    nrs = [n for n in (nrs or []) if n]
    if not nrs:
        return None
    if any(n < 0 for n in nrs):
        raise ValueError("Card IDs must be non-negative")
    specials = sorted(n for n in nrs if n >= SPECIAL_THRESHOLD)
    normals = sorted(n for n in nrs if n < SPECIAL_THRESHOLD)

    if len(specials) > 255 or len(normals) > 255:
        raise ValueError("Card segment count exceeds 255")

    b = bytearray()

    # 1. Trainer
    b.append(len(specials))
    for n in specials:
        v = n * 10
        if v > 0xFFFFFF:
            raise ValueError("ID exceeds 3 bytes")
        b.extend([(v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff])

    # 2. Pokémon
    b.append(len(normals))
    for n in normals:
        v = n * 10
        if v > 0xFFFFFF:
            raise ValueError("ID exceeds 3 bytes")
        b.extend([(v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff])

    energy_ids = energy_ids or []
    if len(energy_ids) > 255:
        raise ValueError("Energy count exceeds 255")

    # 3. Energy
    if energy_ids or normals:
        b.append(len(energy_ids))
        b.extend(energy_ids)

    return base64.b64encode(b).decode("utf-8")