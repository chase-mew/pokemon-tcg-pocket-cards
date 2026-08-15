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
import re
import requests
from constants import GITHUB_BASE_URL, PACK_POINTS, PROMO_CARDS_PER_VOLUME, SHINY_PACK_POINTS, TAG_DEFINITIONS
from utils import set_code_to_prefix, compile_tag_matchers
from deck_code import get_deck_builder_nr, create_single_card_code

def fetch_datamine_lookup():
    lookup = {}
    try:
        resp = requests.get("https://cdn.jsdelivr.net/npm/pokemon-tcg-pocket-database@latest/dist/cards.json",
                            timeout=10)
        if resp.status_code == 200:
            for card in resp.json():
                c_set = str(card.get("set", "")).lower()
                c_set = f"p{c_set.split('-')[-1]}" if c_set.startswith("promo-") else c_set.replace("-", "")
                c_num = card.get("number")
                if c_set and c_num is not None:
                    nr = get_deck_builder_nr(card.get("image", ""))  # ponytail: memoize this if dataset gets huge
                    if nr: lookup[(c_set, int(c_num))] = nr
    except requests.RequestException:
        pass
    return lookup

def _to_v4(card):
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

        if raw_text and raw_text == last_raw_text:
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
            num_int = int(re.sub(r"\D", "", card["number"]))
            deck_builder_nr = datamine_lookup.get((prefix.lower(), num_int))
        except ValueError:
            deck_builder_nr = None
        share_code = create_single_card_code(deck_builder_nr)
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
            "subtype": card["subtype"],
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

            # Deck builder references
            "deckBuilderNr": deck_builder_nr,
            "share_code": share_code,

            # Media & Metadata
            "artist": card["artist"],
            "source_url": card["image"],
            "image": f"{GITHUB_BASE_URL}/webp/cards/{prefix}/{num_zfill}.webp",
            "image_png": f"{GITHUB_BASE_URL}/png/cards/{prefix}/{num_zfill}.png",
            "flavour_text": card["flavour_text"],
            "alternate_versions": card["alternate_versions"],
        })

    if mode == "v4":
        return [_to_v4(c) for c in transformed]

    return transformed