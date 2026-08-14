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
"""a silly script to help me refactor image urls for older v.jsons without breaking stuff"""

import json
from constants import V1_JSON_PATH, V2_JSON_PATH, V4_JSON_PATH

for v in (V1_JSON_PATH, V2_JSON_PATH, V4_JSON_PATH):
    with open(v, "r", encoding="utf-8") as f:
        cards = json.load(f)

    for c in cards:
        prefix, num = c["id"].split("-")
        c["image"] = (
            "https://raw.githubusercontent.com/chase-manning/"
            "pokemon-tcg-pocket-cards/refs/heads/main/images/png/cards/"
            f"{prefix}/{num}.png"
        )

    with open(v, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)