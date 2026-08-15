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
r"""Transform raw scraped card data into the output JSON format.

This module takes the card dicts produced by the scraper and enriches
them with art-style classification, pack points, promo volume grouping,
deck-builder numbers, special tags, and canonical image URLs. It
supports two output formats: ``v5`` (the full enriched schema) and
``v4`` (a reduced schema for backward compatibility).
"""

import re
import requests
from constants import SESSION, FLIBUSTIER_PTCGP_DB_URL, GITHUB_BASE_URL, PACK_POINTS, PROMO_CARDS_PER_VOLUME, SHINY_PACK_POINTS, TAG_DEFINITIONS, PARALLEL_FOIL_RARITIES, DEFAULT_TIMEOUT
from utils import set_code_to_prefix, compile_tag_matchers
from deck_code import get_deck_builder_nr

def fetch_datamine_lookup():
    r"""fetch_datamine_lookup() -> dict

    Download the Flibustier PTCGP card database and build a lookup
    table mapping ``(set_code, card_number)`` tuples to deck-builder
    numbers. Returns an empty dict if the download fails or the
    response is not HTTP 200.

    The set codes from the database are normalised to match the
    prefixes used in card IDs: promo codes like ``"promo-a"`` become
    ``"pa"``, and regular codes have hyphens stripped.

    Returns:
        dict: keys are ``(str, int)`` tuples of (set prefix, card
        number). Values are deck-builder number strings. Returns
        ``{}`` on any network error.

    .. note::

        This function makes one HTTP request per call. If
        :func:`transform_cards` is called many times, consider caching
        the result to avoid repeated downloads.
    """
    lookup = {}
    try:
        resp = SESSION.get(FLIBUSTIER_PTCGP_DB_URL, timeout=DEFAULT_TIMEOUT)
        if resp.status_code == 200:
            for card in resp.json():
                c_set = str(card.get("set", "")).lower()
                c_set = f"p{c_set.split('-')[-1]}" if c_set.startswith("promo-") else c_set.replace("-", "")
                c_num = re.sub(r"\D", "", str(card.get("number", "")))
                if c_set and c_num:
                    nr = get_deck_builder_nr(card.get("image", ""))  # memoize this if dataset gets huge
                    if nr: lookup[(c_set, int(c_num))] = nr
    except (requests.RequestException, ValueError):
        pass
    return lookup

def _to_v4(card):
    r"""_to_v4(card) -> dict

    Convert a single v5 card dict into the v4 JSON format. Maps v5
    field names to their v4 equivalents and flattens some fields:
    ``art_style`` is reduced to a ``"Yes"``/``"No"`` ``fullart`` flag,
    and ``hp`` is stringified.

    Args:
        card (dict): a card dict in v5 format, as produced by
            :func:`transform_cards`

    Returns:
        dict: the card in v4 format, with keys ``id``, ``name``,
        ``rarity``, ``pack``, ``health``, ``image``, ``fullart``,
        ``ex``, ``artist``, and ``type``
    """
    return {
        "id": card["id"],
        "name": card["name"],
        "rarity": card["rarity"],
        "pack": card["pack"],
        "health": str(card["health"]) if card["health"] else "",
        "image": card["image_png"],
        "fullart": "Yes" if card.get("art_style") in ("Full Art", "Special Illustration Art", "Immersive Art", "Shiny Full Art") else "No",
        "ex": "Yes" if card["ex"] else "No",
        "artist": card["artist"],
        "type": card["subtype"]
    }

def transform_cards(raw_cards, set_code, expansion_name, mode="v5", release_date=None):
    r"""transform_cards(raw_cards, set_code, expansion_name, mode='v5', release_date=None) -> list of dict

    Transform raw scraped card dicts into the output format used by
    the API. Each card is enriched with:

    - **Art style** (Illustration Art, Full Art, Special Illustration
      Art, Immersive Art, Shiny, Shiny Full Art, Parallel Foil).
      Classification is inferred from rarity sequences and raw text
      duplication between consecutive cards.
    - **Pack points** from ``PACK_POINTS`` or ``SHINY_PACK_POINTS``
      depending on whether the card is shiny. Promo cards get None.
    - **Promo pack volume** grouping for ``P-A`` cards, using
      ``PROMO_CARDS_PER_VOLUME`` to split cards into numbered volumes.
    - **Deck-builder numbers** and **share codes** from the Flibustier
      datamine lookup.
    - **Special tags** (ancient, future, ultra beasts) matched against
      card names using compiled regex patterns.
    - **Image URLs** pointing to the GitHub raw content CDN, in both
      WebP and PNG formats.

    When ``mode`` is ``"v4"``, each card is converted to the v4
    format via :func:`_to_v4` before returning.

    Args:
        raw_cards (list of dict): cards as returned by
            :func:`scrape_cards`, in card-number order
        set_code (str): the set code (e.g. ``"a1"``, ``"P-A"``)
        expansion_name (str): human-readable expansion name
            (e.g. ``"Genetic Apex"``)
        mode (str): output format. ``"v5"`` for the full enriched
            schema, ``"v4"`` for the reduced backward-compatible
            schema. Default: ``"v5"``
        release_date (str or None): release date in ``"YYYY-MM-DD"``
            format, included in each card's output. Default: ``None``

    Returns:
        list of dict: one transformed card dict per input card. In
        v5 mode each dict has about 30 keys spanning identity,
        classification, gameplay, deck-builder, and media fields.
        In v4 mode each dict has the 10 v4 keys.

    .. note::

        Art style detection depends on the order of cards in
        ``raw_cards`` matching the website's rarity progression.
        Reordering or filtering ``raw_cards`` before calling this
        function can misclassify art styles, since the logic tracks
        state transitions (first three-star, first trainer full art)
        across consecutive cards.

    .. note::

        This function calls :func:`fetch_datamine_lookup` internally,
        which makes an HTTP request. If you are transforming multiple
        sets in one run, the lookup is re-downloaded each time.

    Example::

        >>> cards = scrape_cards("a1")
        >>> transformed = transform_cards(cards, "a1", "Genetic Apex")
        >>> transformed[0]["id"]
        'a1-001'
        >>> transformed[0]["name"]
        'Bulbasaur'
    """
    prefix = set_code_to_prefix(set_code)
    is_pa = set_code == "P-A"
    is_promo = set_code.startswith("P-")
    specific_packs = {c["pack"] for c in raw_cards if c["pack"] != "Every pack"}
    promo_volume, promo_volume_count = 1, 0
    seen_three_star, seen_trainer_fa = False, False
    in_fullart, in_sia = False, False
    last_raw_text, prev_rarity = "", ""
    datamine_lookup = fetch_datamine_lookup()
    tag_matchers = compile_tag_matchers(TAG_DEFINITIONS)

    transformed = []
    for card in raw_cards:
        num_zfill = card["number"].zfill(3)
        raw_text = card.get("raw_text", "")
        rarity = card["rarity"]
        shiny = False
        art_style = None

        if rarity == "☆☆☆":
            seen_three_star, art_style = True, "Immersive Art"
        elif seen_three_star and rarity == "☆":
            shiny, art_style = True, "Shiny"
        elif seen_three_star and rarity == "☆☆":
            shiny, art_style = True, "Shiny Full Art"
        elif rarity == "☆" and not (card["mega"] or card["ex"]):
            art_style = "Illustration Art"
        elif rarity == "☆☆":
            # Full Art run starts at the ☆ -> ☆☆ boundary, ends when SIAs start
            if prev_rarity == "☆" and not in_sia:
                in_fullart = True
            if in_fullart and seen_trainer_fa and (card["mega"] or card["ex"]):
                in_fullart, in_sia = False, True
            if in_sia:
                art_style = "Special Illustration Art"
            elif in_fullart:
                art_style = "Full Art"
                if card["type"] == "Trainer": seen_trainer_fa = True

        if raw_text and raw_text == last_raw_text and rarity in PARALLEL_FOIL_RARITIES:
            art_style = "Parallel Foil"

        if card["type"] == "Trainer": shiny = False
        prev_rarity, last_raw_text = rarity, raw_text

        pack_points = None if is_promo else (SHINY_PACK_POINTS if shiny else PACK_POINTS).get(rarity)
        if is_promo: rarity = "Promo"

        pack = card["pack"]
        if is_pa:
            if pack == "Promo pack":
                promo_volume_count += 1
                if promo_volume_count > PROMO_CARDS_PER_VOLUME:
                    promo_volume, promo_volume_count = promo_volume + 1, 1
                pack = f"Promo V{promo_volume}"
        elif is_promo: pack = expansion_name
        elif pack == "Every pack": pack = f"Shared({expansion_name})" if specific_packs else expansion_name
        elif pack.endswith(" pack"): pack = pack[:-5].strip()

        try:
            deck_builder_nr = datamine_lookup.get((prefix.lower(), int(re.sub(r"\D", "", card["number"]))), 0)
        except ValueError:
            deck_builder_nr = None
        matched_tags = [tag for tag, regex in tag_matchers.items() if regex.search(card["name"])]
        special_tags = matched_tags if matched_tags else None

        transformed.append({
            # Core identifiers
            "id": f"{prefix}-{num_zfill}",
            "name": card["name"],
            "set_code": prefix,
            "set_name": expansion_name,
            "pack": pack,
            "release_date": release_date,

            # Classification
            "type": card["type"],
            "subtype": card["subtype"] or "Unknown",
            "stage": card["stage"],
            "evolves_from": card["evolves_from"],
            "rarity": rarity,
            "pack_points": pack_points,

            # Special properties
            "ex": card["ex"],
            "mega": card["mega"],
            "shiny": shiny,
            "special_tags": special_tags,
            "art_style": art_style,

            # Gameplay mechanics
            "health": card["hp"],
            "retreat": card["retreat"],
            "weakness": card["weakness"],
            "ability": card["ability"],
            "card_text": card["card_text"],
            "attacks": card["attacks"],
            "points": card["points"],

            # Deck builder reference
            "deckBuilderNr": deck_builder_nr,

            # Media & Metadata
            "artist": card["artist"],
            "source_url": card["image"],
            "image": f"{GITHUB_BASE_URL}/webp/cards/{prefix}/{num_zfill}.webp",
            "image_png": f"{GITHUB_BASE_URL}/png/cards/{prefix}/{num_zfill}.png",
            "flavour_text": card["flavour_text"],
            "alternate_versions": [
                {**alt, "set_code": set_code_to_prefix(alt["set_code"].upper())}
                for alt in card["alternate_versions"]
                if f"{set_code_to_prefix(alt['set_code'].upper())}-{str(alt['id']).zfill(3)}" != f"{prefix}-{num_zfill}"
            ],
        })

    if mode == "v4":
        return [_to_v4(c) for c in transformed]

    return transformed