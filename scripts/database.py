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

Writes both per-set files and an aggregated master file. Merges
new cards into existing records, syncs alternate version references
in both directions, and maintains the expansions index.

The v5 data directory (``V5_DIR``) is created on import.
"""

import json
import os
import re
from constants import CARDS_JSON_PATH, EXPANSIONS_JSON_PATH, GITHUB_BASE_URL, PROMO_PREFIXES, V4_JSON_PATH, V5_DIR
from utils import set_code_to_prefix, slugify, _load_existing_json


def minified_path(file_path):
    r"""minified_path(file_path) -> str

    Return the ``.min.json`` sibling of a ``.json`` path. Only the
    suffix is swapped, so a directory containing ``.json`` in its name
    is left alone.

    Args:
        file_path (str): a path ending in ``.json``

    Returns:
        str: the same path with a ``.min.json`` suffix
    """
    root, ext = os.path.splitext(file_path)
    return f"{root}.min{ext}"


def _set_sort_key(set_code):
    r"""_set_sort_key(set_code) -> tuple

    Split a set code into ``(letters, number, suffix)`` so codes sort
    naturally. A plain string sort puts ``b10`` between ``b1`` and
    ``b1a``; this puts it after ``b1a``, which is release order.

    Args:
        set_code (str): a lowercase set prefix such as ``"b1a"`` or ``"pa"``

    Returns:
        tuple: ``(str, int, str)`` sort key
    """
    match = re.match(r"([a-z]+)(\d*)([a-z]*)", set_code)
    if not match:
        return (set_code, 0, "")
    return (match.group(1), int(match.group(2) or 0), match.group(3))


def _card_number(card):
    r"""_card_number(card) -> int

    Card number as an integer, so cards sort 9, 10, 11 rather than
    10, 11, 9.

    Args:
        card (dict): a card with an ``id`` like ``"a1-001"``

    Returns:
        int: the numeric part of the card ID
    """
    return int(card["id"].rsplit("-", 1)[1])


def minify_and_save(data, file_path):
    r"""minify_and_save(data, file_path)

    Write ``data`` as JSON in two files: a pretty-printed version at
    ``file_path`` (indent of 2) and a compact version at the same path
    with ``.json`` replaced by ``.min.json``. Both files use
    ``ensure_ascii=False`` so non-ASCII characters like the rarity
    symbols are preserved.

    Both files are written with explicit LF newlines. Without that,
    running the pipeline on Windows produces CRLF files and every
    regeneration on a Linux CI runner rewrites every line of every
    data file.

    Args:
        data: any JSON-serialisable value (list, dict, etc.)
        file_path (str): destination path for the pretty-printed
            file. The minified path is derived by replacing the
            ``.json`` suffix with ``.min.json``.
    """
    with open(file_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    with open(minified_path(file_path), "w", encoding="utf-8", newline="\n") as f:
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
        card in v5 format as written by :func:`write_set_file` or
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
                        "id": int(lookup[i]["id"].split("-")[1]), "rarity": lookup[i]["rarity"] or "Promo"} for i in
                       group if
                       i in lookup], key=lambda x: (x["set_code"], x["id"]))
        for i in group:
            if i in lookup:
                lookup[i]["alternate_versions"] = [a for a in alts if f"{a['set_code']}-{str(a['id']).zfill(3)}" != i]


def _merge(existing, new_cards):
    r"""_merge(existing, new_cards) -> (list, int)

    Merge ``new_cards`` over ``existing`` by ID, preserving the order of
    existing entries and appending genuinely new ones. Returns the merged
    list and the count of IDs that were not already present.
    """
    merged = {c["id"]: c for c in existing}
    added = len([c for c in new_cards if c["id"] not in merged])
    for c in new_cards:
        merged[c["id"]] = c
    return list(merged.values()), added


def write_set_file(new_cards):
    r"""write_set_file(new_cards) -> int

    Merge ``new_cards`` into the per-set v5 file at
    ``V5_DIR/{prefix}/{prefix}.json``, sorted by card number, and write the
    minified sibling alongside it.

    Args:
        new_cards (list of dict): v5 cards for a single set. Must be
            non-empty; the set prefix is read from ``new_cards[0]["set_code"]``.

    Returns:
        int: how many of ``new_cards`` were not already on disk

    Raises:
        IndexError: if ``new_cards`` is empty
    """
    prefix = new_cards[0]["set_code"]
    set_dir = os.path.join(V5_DIR, prefix)
    os.makedirs(set_dir, exist_ok=True)
    set_json_path = os.path.join(set_dir, f"{prefix}.json")

    merged, added = _merge(_load_existing_json(set_json_path), new_cards)
    merged.sort(key=_card_number)
    minify_and_save(merged, set_json_path)
    return added


def append_to_v4(new_cards):
    r"""append_to_v4(new_cards) -> int

    Merge ``new_cards`` into the single legacy v4 file at ``V4_JSON_PATH``
    and write the minified sibling. Existing cards keep their positions;
    new ones are appended.

    Args:
        new_cards (list of dict): cards already in v4 format, as produced
            by :func:`transformer.downgrade_to_v4`

    Returns:
        int: how many of ``new_cards`` were not already on disk
    """
    os.makedirs(os.path.dirname(V4_JSON_PATH), exist_ok=True)
    existing = _load_existing_json(V4_JSON_PATH) or _load_existing_json(minified_path(V4_JSON_PATH))
    merged, added = _merge(existing, new_cards)
    minify_and_save(merged, V4_JSON_PATH)
    return added


def compile_v5_database():
    r"""compile_v5_database()

    Rebuild the v5 card database from the per-set files on disk.
    Reads all cards, syncs alternate version references, regroups by
    set, saves each set's file, updates the expansions index for each
    set, and writes a master ``cards.json`` containing every card
    sorted by set code then card ID.

    Call this after all sets are scraped and updated, to get the
    final consistent database.

    The steps are:

    1. Read all cards from all set directories under ``V5_DIR``.
    2. Call :func:`sync_alternate_versions` to make alternate version
       references bidirectional.
    3. Group cards by ``set_code``.
    4. For each set, sort by numeric card number and save to
       ``V5_DIR/{prefix}/{prefix}.json``.
    5. For each set, call :func:`update_expansions` to update the
       expansions index.
    6. Sort all cards by natural set order then card number and save
       to ``V5_DIR/cards.json``.
    """
    os.makedirs(V5_DIR, exist_ok=True)
    all_cards = read_all_v5_cards()
    sync_alternate_versions(all_cards)

    set_groups = {}
    for c in all_cards:
        set_groups.setdefault(c["set_code"], []).append(c)

    for prefix, cards in set_groups.items():
        cards.sort(key=_card_number)
        set_dir = os.path.join(V5_DIR, prefix)
        minify_and_save(cards, os.path.join(set_dir, f"{prefix}.json"))
        if cards:
            update_expansions(prefix, cards[0]["set_name"], cards)

    all_cards.sort(key=lambda c: (_set_sort_key(c["set_code"]), _card_number(c)))
    minify_and_save(all_cards, CARDS_JSON_PATH)


def update_expansions(set_code, expansion_name, cards):
    r"""update_expansions(set_code, expansion_name, cards) -> list of dict

    Build or update the entry for a set in the expansions index file
    at ``EXPANSIONS_JSON_PATH``. Creates the entry if it does not
    exist, then fills in the name, release date, total card count,
    pack list, and URLs to the set's JSON files on GitHub.

    Pack detection works by collecting the unique ``pack`` values
    from the cards, excluding packs that start with ``"Shared("`` and
    packs equal to the expansion name, neither of which names a real
    pack. If no unique packs remain, a single generic ``"Booster"``
    pack is created.
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
    is_promo = prefix in PROMO_PREFIXES
    expansions = _load_existing_json(EXPANSIONS_JSON_PATH)

    exp_obj = next((e for e in expansions if e["id"] == prefix), None)
    if not exp_obj:
        exp_obj = {"id": prefix}
        expansions.append(exp_obj)
    exp_obj["name"] = expansion_name

    unique_packs = sorted({c["pack"] for c in cards
                           if not c["pack"].startswith("Shared(") and c["pack"] != expansion_name})
    packs = []

    if not unique_packs:
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