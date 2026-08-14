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
from constants import GITHUB_BASE_URL, PACK_POINTS, PROMO_CARDS_PER_VOLUME, SHINY_PACK_POINTS
from utils import set_code_to_prefix

def transform_cards(raw_cards, set_code, expansion_name, release_date=None):
    prefix = set_code_to_prefix(set_code)
    is_pa = set_code == "P-A"
    is_promo = set_code.startswith("P-")
    specific_packs = {c["pack"] for c in raw_cards if c["pack"] != "Every pack"}
    promo_volume, promo_volume_count = 1, 0
    seen_three_star, seen_trainer_fa = False, False
    in_fullart, in_sia = False, False
    last_raw_text, prev_rarity = "", ""

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

        transformed.append({
            # Identification
            "id": f"{prefix}-{num_zfill}",
            "name": card["name"],
            "set": prefix,
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
            "art_style": art_style,
            "points": card["points"],

            # Stats
            "health": card["hp"],
            "retreat": card["retreat"],
            "weakness": card["weakness"],

            # Abilities & Attacks
            "ability": card["ability"],
            "card_text": card["card_text"],
            "attacks": card["attacks"],

            # Metadata
            "artist": card["artist"],
            "source_url": card["image"],
            "image": f"{GITHUB_BASE_URL}/webp/cards/{prefix}/{num_zfill}.webp",
            "image_png": f"{GITHUB_BASE_URL}/png/cards/{prefix}/{num_zfill}.png",
        })
    return transformed