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
"""Project v5 cards onto the per-consumer payload shapes.

Table-driven: :data:`SHARD_VARIANTS` lists every variant once with the
builder that projects it, and :func:`compile_projections` walks that table
a single time over an already-loaded card list. The legacy six
``compile_*_database`` wrappers still exist for standalone use, but
``compile_v5_database`` reaches this module with its one read instead of
re-reading the disk per variant.
"""

import json
import os

from constants import (CORE_RARITIES, GAMEPLAY_FIELDS,
                       GAMEPLAY_NO_IMAGE_FIELDS, UNIVERSAL_CARD_FIELDS,
                       V5_COLLECTION_CARDS_PATH, V5_COLLECTION_NO_IMAGE_CARDS_PATH,
                       V5_CORE_CARDS_PATH, V5_CORE_NO_IMAGE_CARDS_PATH, V5_DIR,
                       V5_GAMEPLAY_CARDS_PATH, V5_GAMEPLAY_NO_IMAGE_CARDS_PATH)
from utils import _load_existing_json, slugify


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


# Trainer projections are a fixed subset of the gameplay fields, so derive
# them from the sparse record rather than restating the literal dicts. The
# Fossil family plays as a Basic Pokemon and keeps its combat keys.
GAMEPLAY_TRAINER_FIELDS = (
    "id", "name", "set_code", "type", "subtype",
    "card_text", "deckBuilderNr",
)
GAMEPLAY_TRAINER_FOSSIL_FIELDS = (
    "id", "name", "set_code", "type", "subtype", "stage",
    "health", "weakness", "card_text", "points", "deckBuilderNr",
)


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
                record = _sparse_record(GAMEPLAY_TRAINER_FOSSIL_FIELDS, card)
            else:
                record = _sparse_record(GAMEPLAY_TRAINER_FIELDS, card)
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


COLLECTION_SOURCE_FIELDS = (
    "set_name", "pack", "release_date", "rarity", "pack_points", "art_style",
    "artist", "flavour_text", "alternate_versions", "image", "image_png",
    "ex", "mega", "shiny", "special_tags", "tradable", "sharable", "trade_cost",
)


def build_collection_cards(cards):
    r"""build_collection_cards(cards) -> list of dict

    Project every card onto :data:`COLLECTION_FIELDS`, keeping all 3,879
    prints including the cosmetic rarities the gameplay projections drop.
    Records are sparse: a field that does not apply is omitted. The trading
    fields are copied from the card, which the transformer has already
    derived from :data:`TRADE_RULES`.

    Args:
        cards (list of dict): cards in v5 format

    Returns:
        list of dict: one sparse record per card, in input order
    """
    records = []
    for card in cards:
        record = {field: card[field] for field in UNIVERSAL_CARD_FIELDS}
        record.update({field: card.get(field) for field in COLLECTION_SOURCE_FIELDS if card.get(field) is not None})
        records.append(record)
    return records


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


def shard_path(prefix, variant, v5_dir, minified=False):
    r"""shard_path(prefix, variant, v5_dir, minified=False) -> str

    Path of a per-set variant shard under ``v5_dir``. The full per-set
    file keeps its historical name (``{prefix}.json``); a variant shard
    inserts the variant between prefix and extension
    (``{prefix}.{variant}.json``). Set ``minified`` for the ``.min.json``
    sibling.

    Args:
        prefix (str): lowercase set prefix (e.g. ``"a1"``)
        variant (str): variant name from :data:`SHARD_VARIANTS`
        v5_dir (str): directory the shard is written under
        minified (bool): whether to return the compact path

    Returns:
        str: path to the shard file
    """
    path = os.path.join(v5_dir, prefix, f"{prefix}.{variant}.json")
    return minified_path(path) if minified else path


def write_variant_shards(variant, records, v5_dir):
    r"""write_variant_shards(variant, records, v5_dir)

    Group an in-memory projected record list by ``set_code`` and write one
    per-set shard pair per group. Called with the same projected list that
    produced a root payload, so a shard record is byte-identical to its
    root payload counterpart.

    Args:
        variant (str): variant name from :data:`SHARD_VARIANTS`
        v5_dir (str): directory the shards are written under
        records (list of dict): projected records carrying ``set_code``
    """
    by_set = {}
    for record in records:
        by_set.setdefault(record["set_code"], []).append(record)
    for prefix, group in by_set.items():
        os.makedirs(os.path.join(v5_dir, prefix), exist_ok=True)
        write_json_pair(group, shard_path(prefix, variant, v5_dir))


def compile_projections(cards, v5_dir):
    r"""compile_projections(cards, v5_dir)

    Walk :data:`SHARD_VARIANTS` once over an already-loaded card list,
    calling each variant's builder and writing its root pair and per-set
    shard pairs. ``compile_v5_database`` reaches this with its single read
    so the disk is touched once rather than once per variant.

    Args:
        cards (list of dict): all v5 cards in memory
        v5_dir (str): the directory every root payload and shard is
            written under. Taken from the caller rather than a module
            constant so the caller decides where data lands.
    """
    for variant, url_stem, _root_path, builder in SHARD_VARIANTS:
        records = builder(cards)
        write_json_pair(records, os.path.join(v5_dir, os.path.basename(_root_path)))
        write_variant_shards(variant, records, v5_dir)
