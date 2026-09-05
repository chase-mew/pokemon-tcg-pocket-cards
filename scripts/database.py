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
"""

import json
import os
import re
from constants import (CARDS_JSON_PATH, COLLECTION_FIELDS, CORE_RARITIES,
                       EXPANSIONS_JSON_PATH, GAMEPLAY_FIELDS,
                       GAMEPLAY_NO_IMAGE_FIELDS, GITHUB_BASE_URL, PROMO_PREFIXES, TRADE_RULES,
                       UNIVERSAL_CARD_FIELDS,
                       V4_JSON_PATH, V5_CARDS_URL_BASE, V5_COLLECTION_CARDS_PATH,
                       V5_COLLECTION_NO_IMAGE_CARDS_PATH, V5_CORE_CARDS_PATH,
                       V5_CORE_NO_IMAGE_CARDS_PATH, V5_DIR,
                       V5_GAMEPLAY_CARDS_PATH, V5_GAMEPLAY_NO_IMAGE_CARDS_PATH)
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


def write_json_pair(data, file_path):
    r"""write_json_pair(data, file_path)

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
    write_json_pair(merged, set_json_path)
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
    write_json_pair(merged, V4_JSON_PATH)
    return added


CORE_FIELDS = (
    "id", "name", "set_code", "pack", "type", "subtype", "stage",
    "rarity", "special_tags", "ex", "mega", "health", "points", "deckBuilderNr", "image",
)
CORE_NO_IMAGE_FIELDS = tuple(field for field in CORE_FIELDS if field != "image")


def _sparse_record(fields, card):
    r"""_sparse_record(fields, card) -> dict

    Project ``card`` onto ``fields`` and drop what does not apply. A key
    whose value is None is omitted, and Trainer cards always omit ``ex``
    and ``mega`` because they are never rule-box Pokemon. The result is
    the sparse record shape consumers of the projections expect.

    Args:
        fields (tuple of str): the fields to project in order
        card (dict): a card in v5 format

    Returns:
        dict: the projected record with only applicable keys
    """
    record = {field: card.get(field) for field in fields}
    if card["type"] == "Trainer":
        record.pop("ex", None)
        record.pop("mega", None)
    return {key: value for key, value in record.items() if value is not None}


def _is_playable_trainer(card):
    r"""_is_playable_trainer(card) -> bool

    True for Trainer items that play as Pokemon on the field: the Fossil
    family and Old Amber. They keep their combat fields in the projections.
    """
    name = card["name"]
    return name.endswith("Fossil") or name == "Old Amber"


def build_core_cards(cards):
    r"""build_core_cards(cards) -> list of dict

    Project each gameplay card onto :data:`CORE_FIELDS`, preserving the
    field order of the full payload. Star rares and the Crown Rare are
    cosmetic duplicates of a kept card, so they are dropped. Records are
    sparse: a field that does not apply (a null value, or ``ex`` and
    ``mega`` on a Trainer) is omitted. Fossil items keep their playable
    ``stage``, ``health`` and ``points``, so those survive on them.

    Args:
        cards (list of dict): cards in v5 format

    Returns:
        list of dict: one sparse record per kept card, in input order
    """
    return [
        _sparse_record(CORE_FIELDS, card)
        for card in cards
        if card["rarity"] in CORE_RARITIES
    ]


def compile_core_database():
    r"""compile_core_database() -> int

    Read every v5 card, project it onto :data:`CORE_FIELDS` and write the
    result through :func:`write_json_pair`, which produces both
    ``cards.core.json`` and ``cards.core.min.json``.

    Returns:
        int: the number of core records written
    """
    cards = build_core_cards(read_all_v5_cards())
    write_json_pair(cards, V5_CORE_CARDS_PATH)
    write_variant_shards("core", cards)
    return len(cards)


def _build_gameplay_records(cards, fields):
    r"""Build gameplay records from ``cards`` onto ``fields``.

    Shared by the with-image and no-image variants so the trainer and
    Fossil branches are not duplicated. ``fields`` carries ``image`` for
    the with-image payload and omits it for the no-image sister.

    Args:
        cards (list of dict): cards in v5 format
        fields (tuple of str): gameplay field projection, image present
            or absent

    Returns:
        list of dict: one sparse record per kept card, in input order
    """
    with_image = "image" in fields
    records = []
    for card in cards:
        if card["rarity"] not in CORE_RARITIES:
            continue
        if card["type"] == "Trainer":
            if _is_playable_trainer(card):
                record = {
                    "id": card["id"], "name": card["name"],
                    "set_code": card["set_code"], "type": card["type"],
                    "subtype": card["subtype"], "stage": card["stage"],
                    "health": card["health"], "weakness": card["weakness"],
                    "card_text": card["card_text"],
                    "points": card["points"],
                    "deckBuilderNr": card["deckBuilderNr"],
                }
            else:
                record = {
                    "id": card["id"], "name": card["name"],
                    "set_code": card["set_code"], "type": card["type"],
                    "subtype": card["subtype"],
                    "card_text": card["card_text"],
                    "deckBuilderNr": card["deckBuilderNr"],
                }
            if with_image:
                record["image"] = card["image"]
            records.append(record)
        else:
            records.append(_sparse_record(fields, card))
    return records


def build_gameplay_cards(cards):
    r"""build_gameplay_cards(cards) -> list of dict

    Project each card onto :data:`GAMEPLAY_FIELDS`, keeping only the
    gameplay rarities. Records are sparse: a field that does not apply is
    omitted. Trainer records are trimmed to the fields the game exposes on
    them. A non-Fossil Trainer keeps only its identity, subtype, effect
    text, deck number and image. A Fossil item, which plays as a 40-HP
    Basic colourless Pokemon, additionally carries its ``stage``,
    ``health``, ``points`` and ``weakness``. Pokemon records keep the full
    combat projection, omitting only null values.

    Args:
        cards (list of dict): cards in v5 format

    Returns:
        list of dict: one sparse record per kept card, in input order
    """
    return _build_gameplay_records(cards, GAMEPLAY_FIELDS)


def build_gameplay_no_image_cards(cards):
    r"""build_gameplay_no_image_cards(cards) -> list of dict

    The no-image sister of the gameplay payload: the same records as
    :func:`build_gameplay_cards` with the ``image`` key dropped. Kept for
    consumers who serve images from their own CDN.

    Args:
        cards (list of dict): cards in v5 format

    Returns:
        list of dict: one sparse record per kept card, in input order
    """
    return _build_gameplay_records(cards, GAMEPLAY_NO_IMAGE_FIELDS)


def compile_gameplay_database():
    r"""compile_gameplay_database() -> int

    Read every v5 card, project it onto :data:`GAMEPLAY_FIELDS` and write the
    result through :func:`write_json_pair`, which produces both
    ``cards.gameplay.json`` and ``cards.gameplay.min.json``.

    Returns:
        int: the number of gameplay records written
    """
    cards = build_gameplay_cards(read_all_v5_cards())
    write_json_pair(cards, V5_GAMEPLAY_CARDS_PATH)
    write_variant_shards("gameplay", cards)
    return len(cards)


def compile_gameplay_no_image_database():
    r"""compile_gameplay_no_image_database() -> int

    Write the no-image gameplay payload (both ``cards.gameplay.no-image.json``
    and ``cards.gameplay.no-image.min.json``) through :func:`write_json_pair`.

    Returns:
        int: the number of no-image gameplay records written
    """
    cards = build_gameplay_no_image_cards(read_all_v5_cards())
    write_json_pair(cards, V5_GAMEPLAY_NO_IMAGE_CARDS_PATH)
    write_variant_shards("gameplay.no-image", cards)
    return len(cards)


def build_core_no_image_cards(cards):
    r"""build_core_no_image_cards(cards) -> list of dict

    Project each kept card onto :data:`CORE_NO_IMAGE_FIELDS`, reusing the
    core filter and the sparse projection with the ``image`` field dropped.

    Args:
        cards (list of dict): cards in v5 format

    Returns:
        list of dict: one sparse record per kept card, in input order
    """
    return [
        _sparse_record(CORE_NO_IMAGE_FIELDS, card)
        for card in cards
        if card["rarity"] in CORE_RARITIES
    ]


def compile_core_no_image_database():
    r"""compile_core_no_image_database() -> int

    Read every v5 card, project it onto :data:`CORE_NO_IMAGE_FIELDS` and
    write the result through :func:`write_json_pair`, which produces both
    ``cards.core.no-image.json`` and ``cards.core.no-image.min.json``.

    Returns:
        int: the number of no-image core records written
    """
    cards = build_core_no_image_cards(read_all_v5_cards())
    write_json_pair(cards, V5_CORE_NO_IMAGE_CARDS_PATH)
    write_variant_shards("core.no-image", cards)
    return len(cards)


COLLECTION_SOURCE_FIELDS = tuple(f for f in COLLECTION_FIELDS if f not in ("tradable", "sharable", "trade_cost"))


def build_collection_cards(cards):
    r"""build_collection_cards(cards) -> list of dict

    Project every card onto :data:`COLLECTION_FIELDS`, keeping all 3,879
    prints including the cosmetic rarities the gameplay projections drop.
    Records are sparse: a field that does not apply is omitted. The trading
    fields are derived from :data:`TRADE_RULES` keyed on rarity, shiny and
    art style, so a card whose combination the table does not cover fails
    loudly instead of guessing a rule.

    Args:
        cards (list of dict): cards in v5 format

    Returns:
        list of dict: one sparse record per card, in input order
    """
    records = []
    for card in cards:
        record = {field: card[field] for field in UNIVERSAL_CARD_FIELDS}
        record.update({field: card.get(field) for field in COLLECTION_SOURCE_FIELDS if card.get(field) is not None})
        tradable, sharable, trade_cost = TRADE_RULES[(card["rarity"], card["shiny"], card["art_style"])]
        record["tradable"] = tradable
        record["sharable"] = sharable
        record["trade_cost"] = trade_cost
        records.append(record)
    return records


def compile_collection_database():
    r"""compile_collection_database() -> int

    Write the collection payload (both ``cards.collection.json`` and
    ``cards.collection.min.json``) through :func:`write_json_pair`.

    Returns:
        int: the number of collection records written
    """
    cards = build_collection_cards(read_all_v5_cards())
    write_json_pair(cards, V5_COLLECTION_CARDS_PATH)
    write_variant_shards("collection", cards)
    return len(cards)


def build_collection_no_image_cards(cards):
    r"""build_collection_no_image_cards(cards) -> list of dict

    The no-image sister of the collection payload: the records that
    :func:`build_collection_cards` produces with the ``image`` and
    ``image_png`` keys dropped. The collection trade-rule derivation runs
    exactly once, in :func:`build_collection_cards`, so the two payloads
    cannot drift on tradable and sharable values.

    Args:
        cards (list of dict): cards in v5 format

    Returns:
        list of dict: one sparse record per card, in input order, with no
        image URL keys
    """
    return [
        {key: value for key, value in record.items()
         if key not in ("image", "image_png")}
        for record in build_collection_cards(cards)
    ]


def compile_collection_no_image_database():
    r"""compile_collection_no_image_database() -> int

    Write the no-image collection payload (both
    ``cards.collection.no-image.json`` and
    ``cards.collection.no-image.min.json``) through :func:`write_json_pair`.

    Returns:
        int: the number of no-image collection records written
    """
    cards = build_collection_no_image_cards(read_all_v5_cards())
    write_json_pair(cards, V5_COLLECTION_NO_IMAGE_CARDS_PATH)
    write_variant_shards("collection.no-image", cards)
    return len(cards)


SHARD_VARIANTS = (
    # (variant, url stem, root payload path, builder)
    ("core", "cards_core", V5_CORE_CARDS_PATH, build_core_cards),
    ("core.no-image", "cards_core_no_image", V5_CORE_NO_IMAGE_CARDS_PATH,
     build_core_no_image_cards),
    ("gameplay", "cards_gameplay", V5_GAMEPLAY_CARDS_PATH, build_gameplay_cards),
    ("gameplay.no-image", "cards_gameplay_no_image", V5_GAMEPLAY_NO_IMAGE_CARDS_PATH,
     build_gameplay_no_image_cards),
    ("collection", "cards_collection", V5_COLLECTION_CARDS_PATH, build_collection_cards),
    ("collection.no-image", "cards_collection_no_image", V5_COLLECTION_NO_IMAGE_CARDS_PATH,
     build_collection_no_image_cards),
)


def shard_path(prefix, variant, minified=False):
    r"""shard_path(prefix, variant, minified=False) -> str

    Path of a per-set variant shard under ``V5_DIR``. The full per-set
    file keeps its historical name (``{prefix}.json``); a variant shard
    inserts the variant between prefix and extension
    (``{prefix}.{variant}.json``). Set ``minified`` for the ``.min.json``
    sibling.

    Args:
        prefix (str): lowercase set prefix (e.g. ``"a1"``)
        variant (str): variant name from :data:`SHARD_VARIANTS`
        minified (bool): whether to return the compact path

    Returns:
        str: path to the shard file
    """
    path = os.path.join(V5_DIR, prefix, f"{prefix}.{variant}.json")
    return minified_path(path) if minified else path


def write_variant_shards(variant, records):
    r"""write_variant_shards(variant, records)

    Group an in-memory projected record list by ``set_code`` and write one
    per-set shard pair per group. Called with the same projected list that
    produced a root payload, so a shard record is byte-identical to its
    root payload counterpart.

    Args:
        variant (str): variant name from :data:`SHARD_VARIANTS`
        records (list of dict): projected records carrying ``set_code``
    """
    by_set = {}
    for record in records:
        by_set.setdefault(record["set_code"], []).append(record)
    for prefix, group in by_set.items():
        write_json_pair(group, shard_path(prefix, variant))


def compile_v5_database():
    r"""compile_v5_database()

    Rebuild the v5 card database from the per-set files on disk.
    Reads all cards, syncs alternate version references, regroups by
    set, saves each set's file, builds the expansions index in
    memory, and writes a master ``cards.json`` containing every card
    sorted by set code then card ID.

    Call this after all sets are scraped and updated, to get the
    final consistent database.

    The steps are:

    1. Read all cards from all set directories under ``V5_DIR``.
    2. Call :func:`sync_alternate_versions` to make alternate version
       references bidirectional.
    3. Group cards by ``set_code``.
    4. For each set, sort by numeric card number, save to
       ``V5_DIR/{prefix}/{prefix}.json``, and build its expansion
       entry with :func:`build_expansion_entry`.
    5. Write the whole expansions index in one call, once every set
       has been processed.
    6. Sort all cards by natural set order then card number and save
       to ``V5_DIR/cards.json``.
    """
    os.makedirs(V5_DIR, exist_ok=True)
    all_cards = read_all_v5_cards()
    sync_alternate_versions(all_cards)

    set_groups = {}
    for c in all_cards:
        set_groups.setdefault(c["set_code"], []).append(c)

    expansions = _load_existing_json(EXPANSIONS_JSON_PATH)
    by_id = {e["id"]: e for e in expansions}

    for prefix, cards in set_groups.items():
        cards.sort(key=_card_number)
        write_json_pair(cards, os.path.join(V5_DIR, prefix, f"{prefix}.json"))
        if cards:
            entry = build_expansion_entry(prefix, cards[0]["set_name"], cards)
            if prefix in by_id:
                by_id[prefix].update(entry)
            else:
                expansions.append(entry)
                by_id[prefix] = entry

    write_json_pair(expansions, EXPANSIONS_JSON_PATH)

    all_cards.sort(key=lambda c: (_set_sort_key(c["set_code"]), _card_number(c)))
    write_json_pair(all_cards, CARDS_JSON_PATH)

    compile_core_database()
    compile_gameplay_database()
    compile_gameplay_no_image_database()
    compile_core_no_image_database()
    compile_collection_database()
    compile_collection_no_image_database()


def build_expansion_entry(prefix, expansion_name, cards):
    r"""build_expansion_entry(prefix, expansion_name, cards) -> dict

    Build one expansion index entry. Pure: reads nothing and writes
    nothing, so the caller controls when the index hits disk.

    Packs come from the distinct ``pack`` values, excluding the
    ``"Shared(...)"`` marker and the expansion name itself, neither of
    which names a real pack. A set with no named packs gets a single
    generic ``"Booster"``. Promo packs have no artwork in the game, so
    their image URLs are None.

    Args:
        prefix (str): lowercase set prefix (e.g. ``"a1"``, ``"pa"``)
        expansion_name (str): human-readable name
        cards (list of dict): every card in the set

    Returns:
        dict: ``id``, ``name``, ``release_date``, ``total_cards``,
        ``cards_url``, ``cards_url_min``, ``packs``
    """
    is_promo = prefix in PROMO_PREFIXES

    def pack_entry(pack_id, name):
        return {
            "id": pack_id,
            "name": name,
            "image": None if is_promo else f"{GITHUB_BASE_URL}/webp/packs/{pack_id}.webp",
            "image_png": None if is_promo else f"{GITHUB_BASE_URL}/png/packs/{pack_id}.png",
        }

    unique_packs = sorted({c["pack"] for c in cards
                           if not c["pack"].startswith("Shared(") and c["pack"] != expansion_name})
    packs = ([pack_entry(f"{prefix}-booster", "Booster")] if not unique_packs
             else [pack_entry(f"{prefix}-{slugify(name)}", name) for name in unique_packs])

    dates = [c["release_date"] for c in cards if c.get("release_date")]
    entry = {
        "id": prefix,
        "name": expansion_name,
        "release_date": min(dates) if dates else None,
        "total_cards": len(cards),
        "cards_url": f"{V5_CARDS_URL_BASE}/{prefix}/{prefix}.json",
        "cards_url_min": f"{V5_CARDS_URL_BASE}/{prefix}/{prefix}.min.json",
    }
    for variant, url_stem, _path, _builder in SHARD_VARIANTS:
        entry[f"{url_stem}_url"] = f"{V5_CARDS_URL_BASE}/{prefix}/{prefix}.{variant}.json"
        entry[f"{url_stem}_url_min"] = (
            f"{V5_CARDS_URL_BASE}/{prefix}/{prefix}.{variant}.min.json")
    entry["packs"] = packs
    return entry


def update_expansions(set_code, expansion_name, cards):
    r"""update_expansions(set_code, expansion_name, cards) -> list of dict

    Build or update the entry for a set in the expansions index file
    at ``EXPANSIONS_JSON_PATH``. Creates the entry if it does not
    exist, then fills in the name, release date, total card count,
    pack list, and URLs to the set's JSON files on GitHub.

    A convenience wrapper for single-set updates: it reads the whole
    index, builds one entry with :func:`build_expansion_entry`, and
    writes the whole index back. :func:`compile_v5_database` updates
    every set in one pass instead, so it batches the writes itself
    rather than calling this per set.

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
    expansions = _load_existing_json(EXPANSIONS_JSON_PATH)
    entry = build_expansion_entry(prefix, expansion_name, cards)

    existing = next((e for e in expansions if e["id"] == prefix), None)
    if existing:
        existing.update(entry)
    else:
        expansions.append(entry)

    write_json_pair(expansions, EXPANSIONS_JSON_PATH)
    return entry["packs"]