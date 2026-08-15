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
r"""Persist card data to JSON files on disk.

Writes both per-set files and an aggregated master file. Merges new
cards into existing records, synchronises alternate version references
bidirectionally across cards, and maintains the expansions index.

The v5 data directory (``V5_DIR``) is created on import.
"""

import json
import os
from constants import EXPANSIONS_JSON_PATH, GITHUB_BASE_URL, V4_JSON_PATH, V5_DIR, CURRENT_VERSION
from utils import set_code_to_prefix, slugify, _load_existing_json


def minify_and_save(data, file_path):
    r"""minify_and_save(data, file_path)

    Write ``data`` as JSON in two files: a pretty-printed version at
    ``file_path`` (indent of 2) and a compact version at the same path
    with ``.json`` replaced by ``.min.json``. Both files use
    ``ensure_ascii=False`` so non-ASCII characters like the rarity
    symbols are preserved.

    Args:
        data: any JSON-serialisable value (list, dict, etc.)
        file_path (str): destination path for the pretty-printed
            file. The minified path is derived by replacing the
            ``.json`` suffix with ``.min.json``.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    min_path = file_path.replace(".json", ".min.json")
    with open(min_path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(',', ':'), ensure_ascii=False)


def read_all_v5_cards():
    r"""read_all_v5_cards() -> list of dict

    Read every card from every set stored under ``V5_DIR``. Each
    subdirectory of ``V5_DIR`` is named after a set prefix (e.g.
    ``a1``, ``pa``). The JSON file inside has the same name as the
    directory (e.g. ``a1/a1.json``). Cards from all sets are collected
    into a single flat list.

    Returns:
        list of dict: all cards across all sets. Each dict is the
        card in v5 format as written by :func:`update_cards` or
        :func:`compile_v5_database`.
    """
    cards = []
    for item in os.listdir(V5_DIR):
        set_dir = os.path.join(V5_DIR, item)
        if os.path.isdir(set_dir):
            cards.extend(_load_existing_json(os.path.join(set_dir, f"{item}.json")))
    return cards


def sync_alternate_versions(all_cards):
    r"""sync_alternate_versions(all_cards)

    Make alternate version references bidirectional. When card A
    lists card B in its ``alternate_versions`` array, card B should
    also list card A. This function groups all cards connected through
    alternate version references using a union-find (disjoint set)
    data structure, then replaces each card's ``alternate_versions``
    list with all other cards in its group.

    The grouping works as follows: for each card, the card's ID is
    unioned with the ID of every alternate version it references.
    After all unions are done, cards sharing a root are in the same
    group. Each group with two or more members gets its
    ``alternate_versions`` lists rewritten to include every other
    member, sorted by set code then card number.

    .. note::

        This function mutates the card dicts in ``all_cards`` in
        place. It modifies the ``alternate_versions`` key on each
        card that belongs to a multi-card group.

    .. note::

        Alternate version IDs that do not correspond to any card in
        ``all_cards`` (for example, cards from a set not yet scraped)
        are included in the union-find but are skipped when building
        the final alternate versions lists. They still influence
        grouping: if card A references card B, and card B is not in
        the list, card A still ends up in a group of size 1 and gets
        an empty alternate versions list.

    Args:
        all_cards (list of dict): all cards across all sets. Each
            card must have an ``id`` key (str, e.g. ``"a1-001"``) and
            an ``alternate_versions`` key (list of dict, where each
            dict has ``set_code`` and ``id`` keys).
    """
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
        alts = sorted([{"set_code": lookup[i]["set_code"], "set_name": lookup[i]["set_name"],
                        "id": int(lookup[i]["id"].split("-")[1]), "rarity": lookup[i]["rarity"]} for i in group if
                       i in lookup], key=lambda x: (x["set_code"], x["id"]))
        for i in group:
            if i in lookup:
                lookup[i]["alternate_versions"] = [a for a in alts if f"{a['set_code']}-{str(a['id']).zfill(3)}" != i]


def update_cards(new_cards, version):
    r"""update_cards(new_cards, version) -> int

    Merge ``new_cards`` into the JSON file for the given schema
    version. New cards overwrite existing ones with the same ID.
    Returns the number of cards that were not already present.

    For the current version (``CURRENT_VERSION``, i.e. v5), cards are
    saved to a per-set file at ``V5_DIR/{prefix}/{prefix}.json``,
    where ``prefix`` is the set code of the first card in
    ``new_cards``. The merged list is sorted by card ID before
    saving.

    For older versions, cards are appended to the single file at
    ``V4_JSON_PATH``. The merge is order-preserving: existing cards
    keep their positions, and new cards are appended at the end.

    Args:
        new_cards (list of dict): cards to merge in. Each card must
            have an ``id`` key and, for v5, a ``set_code`` key.
        version (int): schema version. If equal to
            ``CURRENT_VERSION``, the v5 per-set path is used.
            Otherwise the v4 single-file path is used.

    Returns:
        int: the number of cards in ``new_cards`` whose ID was not
        already present in the existing data

    .. note::

        When ``version`` equals ``CURRENT_VERSION``, this function
        assumes ``new_cards`` is non-empty because it reads the set
        prefix from ``new_cards[0]["set_code"]``. Passing an empty
        list will raise ``IndexError``.
    """
    os.makedirs(V5_DIR, exist_ok=True)
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
    r"""compile_v5_database()

    Rebuild the v5 card database from the per-set files on disk.
    Reads all cards, syncs alternate version references, regroups by
    set, saves each set's file, updates the expansions index for each
    set, and writes a master ``cards.json`` containing every card
    sorted by set code then card ID.

    This is the full rebuild path. It should be called after all
    sets have been scraped and updated, to produce the final
    consistent state of the database.

    The steps are:

    1. Read all cards from all set directories under ``V5_DIR``.
    2. Call :func:`sync_alternate_versions` to make alternate version
       references bidirectional.
    3. Group cards by ``set_code``.
    4. For each set, sort by card ID and save to
       ``V5_DIR/{prefix}/{prefix}.json``.
    5. For each set, call :func:`update_expansions` to update the
       expansions index.
    6. Sort all cards by ``(set_code, id)`` and save to
       ``V5_DIR/cards.json``.
    """
    os.makedirs(V5_DIR, exist_ok=True)
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
    r"""update_expansions(set_code, expansion_name, cards) -> list of dict

    Build or update the entry for a set in the expansions index file
    at ``EXPANSIONS_JSON_PATH``. Creates the entry if it does not
    exist, then fills in the name, release date, total card count,
    pack list, and URLs to the set's JSON files on GitHub.

    Pack detection works by collecting the unique ``pack`` values
    from the cards, excluding packs that start with ``"Shared("``.
    If no unique packs remain, or the only pack is the expansion
    name itself, a single generic ``"Booster"`` pack is created.
    Otherwise one pack entry is created per unique pack name, with
    the pack name slugified for the pack ID and image filenames.

    The release date is the earliest ``release_date`` among the
    cards, or ``None`` if no card has one.

    Args:
        set_code (str): the set code (e.g. ``"A1"``, ``"P-A"``)
        expansion_name (str): human-readable expansion name
            (e.g. ``"Genetic Apex"``)
        cards (list of dict): all cards in the set. Each card must
            have ``pack``, ``release_date``, and ``set_code`` keys.

    Returns:
        list of dict: the pack objects for this expansion. Each dict
        has ``id``, ``name``, ``image``, and ``image_png`` keys. The
        image URLs point to the GitHub raw content CDN.
    """
    prefix = set_code_to_prefix(set_code)
    is_promo = prefix.startswith("p")
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
            "image": None if is_promo else f"{GITHUB_BASE_URL}/webp/packs/{prefix}-booster.webp",
            "image_png": None if is_promo else f"{GITHUB_BASE_URL}/png/packs/{prefix}-booster.png"
        })
    else:
        for pack_name in unique_packs:
            slug = slugify(pack_name)
            packs.append({
                "id": f"{prefix}-{slug}",
                "name": pack_name,
                "image": None if is_promo else f"{GITHUB_BASE_URL}/webp/packs/{prefix}-{slug}.webp",
                "image_png": None if is_promo else f"{GITHUB_BASE_URL}/png/packs/{prefix}-{slug}.png"
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