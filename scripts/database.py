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
import json
from constants import EXPANSIONS_JSON_PATH, GITHUB_BASE_URL, V4_JSON_PATH, V5_JSON_PATH
from utils import set_code_to_prefix, slugify

def update_cards(new_cards, version):
    """Append cards that aren't already in the vN database."""
    path_map = {4: V4_JSON_PATH, 5: V5_JSON_PATH}
    json_path = path_map[version]

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = []

    seen = {c["id"] for c in existing}
    to_add = [card for card in new_cards if card["id"] not in seen]

    if not to_add:
        return 0

    existing.extend(to_add)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return len(to_add)


def update_expansions(set_code, expansion_name, cards):
    prefix = set_code_to_prefix(set_code)
    try:
        with open(EXPANSIONS_JSON_PATH, "r", encoding="utf-8") as f: expansions = json.load(f)
    except FileNotFoundError: expansions = []

    for exp in expansions:
        if exp["id"] == prefix: return exp["packs"]

    unique_packs = sorted({c["pack"] for c in cards if not c["pack"].startswith("Shared(")})
    packs = []

    if not unique_packs or unique_packs == [expansion_name]:
        packs.append({"id": f"{prefix}-booster", "name": "Booster", "image": f"{GITHUB_BASE_URL}/webp/packs/{prefix}-booster.webp", "image_png": f"{GITHUB_BASE_URL}/png/packs/{prefix}-booster.png"})
    else:
        for pack_name in unique_packs:
            slug = slugify(pack_name)
            packs.append({"id": f"{prefix}-{slug}", "name": pack_name, "image": f"{GITHUB_BASE_URL}/webp/packs/{prefix}-{slug}.webp", "image_png": f"{GITHUB_BASE_URL}/png/packs/{prefix}-{slug}.png"})

    expansions.append({"id": prefix, "name": expansion_name, "packs": packs})
    with open(EXPANSIONS_JSON_PATH, "w", encoding="utf-8") as f: json.dump(expansions, f, indent=2, ensure_ascii=False)
    return packs
