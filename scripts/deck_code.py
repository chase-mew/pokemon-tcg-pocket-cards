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
import base64
import re

TRAINER_OFFSET = 1_000_000
SPECIAL_THRESHOLD = 100_000

def get_deck_builder_nr(image_filename):
    match = re.search(r"c([A-Z]+)_\d+_(\d{6})_", str(image_filename or ""))
    if not match:
        return None
    raw = int(match.group(2))
    if raw % 10 != 0:
        return None
    nr = raw // 10
    return TRAINER_OFFSET + nr if match.group(1) == "TR" else nr

def create_single_card_code(nr):
    if not isinstance(nr, int) or nr <= 0:
        return None

    is_special = nr >= SPECIAL_THRESHOLD
    specials = [nr] if is_special else []
    normals = [] if is_special else [nr]

    bytes_arr = bytearray()
    for group in [specials, normals]:
        bytes_arr.append(len(group) & 0xff)
        for n in group:
            v = n * 10
            bytes_arr.append((v >> 16) & 0xff)
            bytes_arr.append((v >> 8) & 0xff)
            bytes_arr.append(v & 0xff)

    bytes_arr.append(0)
    return base64.b64encode(bytes_arr).decode("utf-8")