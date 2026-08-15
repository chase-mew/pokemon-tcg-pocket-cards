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
import os
from constants import EXPANSIONS_JSON_PATH, GITHUB_BASE_URL, V4_JSON_PATH, V5_DIR, CURRENT_VERSION
from utils import set_code_to_prefix, slugify, _load_existing_json

os.makedirs(V5_DIR, exist_ok=True)


def minify_and_save(data, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    min_path = file_path.replace(".json", ".min.json")
    with open(min_path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(',', ':'), ensure_ascii=False)


def read_all_v5_cards():
    cards = []
    for item in os.listdir(V5_DIR):
        cards.extend(_load_existing_json(os.path.join(V5_DIR, item, f"{item}.json")))
    return cards


def sync_alternate_versions(all_cards):
    parent = {}

    def find(i):
        if parent.setdefault(i, i) == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    for c in all_cards:
        for alt in c.get("alternate_versions", []):
            parent[find(c["id"])] = find(f"{alt['set_code']}-{str(alt['id']).zfill(3)}")

    groups = {}
    for node in parent:
        groups.setdefault(find(node), set()).add(node)

    lookup = {c["id"]: c for c in all_cards}
    for group in groups.values():
        if len(group) < 2:
            continue
        alts = sorted([{"set_code": lookup[i]["set_code"], "set_name": lookup[i]["set_name"],
                        "id": int(lookup[i]["id"].split("-")[1]), "rarity": lookup[i]["rarity"]} for i in group if
                       i in lookup], key=lambda x: (x["set_code"], x["id"]))
        for i in group:
            if i in lookup:
                lookup[i]["alternate_versions"] = [a for a in alts if f"{a['set_code']}-{str(a['id']).zfill(3)}" != i]


def update_cards(new_cards, version):
    if version != CURRENT_VERSION:
        existing = _load_existing_json(V4_JSON_PATH)
        seen = {c["id"] for c in existing}
        merged = {c["id"]: c for c in existing}
        for c in new_cards:
            merged[c["id"]] = c
        minify_and_save(list(merged.values()), V4_JSON_PATH)
        return len([c for c in new_cards if c["id"] not in seen])

    prefix = new_cards[0]["set_code"]
    set_dir = os.path.join(V5_DIR, prefix)
    os.makedirs(set_dir, exist_ok=True)
    set_json_path = os.path.join(set_dir, f"{prefix}.json")

    existing = _load_existing_json(set_json_path)
    seen = {c["id"] for c in existing}
    to_add = [card for card in new_cards if card["id"] not in seen]

    merged = {c["id"]: c for c in existing}
    for c in new_cards:
        merged[c["id"]] = c

    final_set_cards = list(merged.values())
    final_set_cards.sort(key=lambda x: x["id"])

    minify_and_save(final_set_cards, set_json_path)
    return len(to_add)


def compile_v5_database():
    all_cards = read_all_v5_cards()
    sync_alternate_versions(all_cards)

    set_groups = {}
    for c in all_cards:
        set_groups.setdefault(c["set_code"], []).append(c)

    for prefix, cards in set_groups.items():
        cards.sort(key=lambda x: x["id"])
        set_dir = os.path.join(V5_DIR, prefix)
        minify_and_save(cards, os.path.join(set_dir, f"{prefix}.json"))
        if cards:
            update_expansions(prefix, cards[0]["set_name"], cards)

    all_cards.sort(key=lambda x: (x["set_code"], x["id"]))
    main_json = os.path.join(V5_DIR, "cards.json")
    minify_and_save(all_cards, main_json)


def update_expansions(set_code, expansion_name, cards):
    prefix = set_code_to_prefix(set_code)
    expansions = _load_existing_json(EXPANSIONS_JSON_PATH)

    exp_obj = next((e for e in expansions if e["id"] == prefix), None)
    if not exp_obj:
        exp_obj = {"id": prefix}
        expansions.append(exp_obj)
    exp_obj["name"] = expansion_name

    unique_packs = sorted({c["pack"] for c in cards if not c["pack"].startswith("Shared(")})
    packs = []

    if not unique_packs or unique_packs == [expansion_name]:
        packs.append({
            "id": f"{prefix}-booster",
            "name": "Booster",
            "image": f"{GITHUB_BASE_URL}/webp/packs/{prefix}-booster.webp",
            "image_png": f"{GITHUB_BASE_URL}/png/packs/{prefix}-booster.png"
        })
    else:
        for pack_name in unique_packs:
            slug = slugify(pack_name)
            packs.append({
                "id": f"{prefix}-{slug}",
                "name": pack_name,
                "image": f"{GITHUB_BASE_URL}/webp/packs/{prefix}-{slug}.webp",
                "image_png": f"{GITHUB_BASE_URL}/png/packs/{prefix}-{slug}.png"
            })

    dates = [c["release_date"] for c in cards if c.get("release_date")]

    exp_obj["release_date"] = min(dates) if dates else None
    exp_obj["total_cards"] = len(cards)
    exp_obj[
        "cards_url"] = f"https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/data/v5/{prefix}/{prefix}.json"
    exp_obj[
        "cards_url_min"] = f"https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/data/v5/{prefix}/{prefix}.min.json"
    exp_obj["packs"] = packs

    minify_and_save(expansions, EXPANSIONS_JSON_PATH)
    return packs