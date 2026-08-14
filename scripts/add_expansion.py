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
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Add a new expansion to the Pokemon TCG Pocket cards database.

Scrapes card data from Limitless TCG, downloads card images, and updates
both the current card database and expansions.json (expansion index).

Usage:
    python scripts/add_expansion.py B2b
    python scripts/add_expansion.py B1 --name "Mega Rising"
    python scripts/add_expansion.py PA              # update Promo-A with new cards
    python scripts/add_expansion.py PB --skip-images
"""

import argparse
import datetime
import io
import json
import os
import re
import sys
import time

from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image
from constants import *

# ---------------------------------------------------------------------------
# Step 0: Helpers
# ---------------------------------------------------------------------------
class NotFound(Exception):
    """Page returned 404. the card doesn't exist, don't retry."""

def normalise_set_code(code):
    """Normalize set code input (e.g. 'PA'/'pa' -> 'P-A', 'PB' -> 'P-B')."""
    cleaned = code.strip().upper().replace("-", "")
    if len(cleaned) == 2 and cleaned[0] == 'P':
        return f"P-{cleaned[1]}"
    return code.strip()

def fetch_page(url):
    for attempt in range(MAX_RETRIES):
        try:
            response = SESSION.get(url, timeout=15)
            if response.status_code == 404:
                raise NotFound(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(1)

def set_code_to_prefix(set_code):
    """Convert set code to card ID prefix (e.g. 'B2b' -> 'b2b', 'P-A' -> 'pa')."""
    if set_code.startswith("P-"):
        return f"p{set_code[2:].lower()}"
    return set_code.lower()

def to_int(text, default=None):
    """'40 HP' -> 40, '100+' -> 100, '' -> default."""
    digits = re.sub(r"\D", "", text or "")
    return int(digits) if digits else default


def parse_release_date(text):
    """'30 Jun 26' -> '2026-06-30'; blank (promo sets) -> None."""
    text = (text or "").strip()
    return datetime.strptime(text, "%d %b %y").strftime("%Y-%m-%d") if text else None


def parse_trainer_subtype(type_text):
    """'Trainer - Pokémon Tool' -> 'Tool'."""
    return next((s for s in TRAINER_SUBTYPES if s in type_text), None)

def clean_text(text):
    """Strip newlines, tabs, and duplicate spaces."""
    if not text: return None
    return re.sub(r'\s+', ' ', text).strip()

# ---------------------------------------------------------------------------
# Step 1: Discover expansion name + release date from Limitless TCG
# ---------------------------------------------------------------------------
def discover_set(set_code):
    """(name, release_date) read from the /cards index table."""
    soup = fetch_page(BASE_URL)
    for row in soup.select("table.sets-table tr"):
        code_el = row.find("span", class_="code")
        if not code_el or code_el.text.strip().lower() != set_code.lower():
            continue
        cells = row.find_all("td")
        code_el.extract()  # leaves just the set name in the first cell
        return clean_text(cells[0].get_text(" ", strip=True)), parse_release_date(cells[1].get_text())

    # not indexed yet: fall back to the set page title, no date
    title = fetch_page(f"{BASE_URL}{set_code}").find("title").text
    return clean_text(title.split(" (")[0].split(" – ")[0]), None


# ---------------------------------------------------------------------------
# Step 2: Scrape all cards
# ---------------------------------------------------------------------------
def extract_card(soup, set_code=""):
    body = soup.find("div", class_="card-text")
    title_el = body.find("p", class_="card-text-title")
    card_number = title_el.find("a")["href"].split("/")[-1]
    name = clean_text(title_el.find("a").text)

    # i.e.: title reads "Caterpie - Grass - 40 HP" (trainers have neither part)
    title_parts = [p.strip() for p in title_el.get_text(" ", strip=True).split(" - ")]
    energy_type = title_parts[1] if len(title_parts) > 2 else None

    type_el = body.find("p", class_="card-text-type")
    type_text = type_el.text.strip()
    type_text_raw = type_el.get_text(" ", strip=True)
    is_trainer = type_text_raw.startswith("Trainer")
    card_type = "Trainer" if is_trainer else "Pokémon"
    subtype = parse_trainer_subtype(type_text_raw) if is_trainer else energy_type

    hp = None if is_trainer else to_int(title_parts[-1])

    # card body only: identical between a print and its parallel foil, unlike the full page
    raw_text = clean_text(body.get_text(" ", strip=True))

    # Trainer effect text = the section right after the title section
    card_text = None
    if is_trainer:
        sections = body.find_all("div", class_="card-text-section", recursive=False)
        if len(sections) > 1 and sections[1].get("class") == ["card-text-section"]:
            card_text = clean_text(sections[1].get_text(" ", strip=True))

    image_div = soup.find("div", class_="card-image")
    image = image_div.find("img")["src"] if image_div and image_div.find("img") else None

    rarity = "Unknown"
    rarity_table = soup.find("table", class_="card-prints-versions")
    if rarity_table:
        current = rarity_table.find("tr", class_="current")
        if current: rarity = clean_text(current.find_all("td")[-1].text)

    pack = "Every pack"
    set_info = soup.find("div", class_="card-prints-current")
    if set_info:
        if set_code == "P-A":
            text = set_info.get_text()
            for keyword in PROMO_A_PACK_KEYWORDS:
                if keyword in text: pack = keyword
        else:
            spans = set_info.find_all("span")
            if spans:
                last_segment = spans[-1].text.strip().split("·")[-1].strip()
                if last_segment.endswith(" pack"): pack = last_segment
    pack = clean_text(pack)

    artist_div = body.find("div", class_="card-text-artist")
    artist = clean_text(artist_div.find("a").text) if artist_div and artist_div.find("a") else "Unknown"

    stage, evolves_from, retreat, weakness = None, None, None, None
    if not is_trainer:
        stage_match = re.search(r"(Basic|Stage 1|Stage 2)", type_text_raw)
        stage = stage_match.group(1) if stage_match else "Unknown"
        if stage in ("Stage 1", "Stage 2"):
            evo_match = re.search(r"Evolves from\s*(.+)", type_text_raw)
            evolves_from = evo_match.group(1).strip() if evo_match else None
        retreat_match = re.search(r"Retreat:\s*(\d+)", raw_text)
        retreat = int(retreat_match.group(1)) if retreat_match else 0
        weakness_match = re.search(r"Weakness:\s*([A-Za-z]+)", raw_text)
        weakness = weakness_match.group(1) if weakness_match else "none"

    ability_div = body.find("div", class_="card-text-ability")
    ability = {"exists": bool(ability_div), "name": None, "effect": None}
    if ability_div:
        ability["name"] = clean_text(ability_div.find("p", class_="card-text-ability-info").text.replace("Ability:", ""))
        ability["effect"] = clean_text(ability_div.find("p", class_="card-text-ability-effect").text)

    ex = "ex" in name.split(" ")
    mega = name.startswith("Mega ") or "Mega Evolution ex rule" in raw_text
    points = None if is_trainer else (3 if mega and ex else 2 if ex else 1)

    attacks = {str(n): {"cost": None, "name": None, "damage": None, "effect": None} for n in (1, 2)}

    for i, atk_div in enumerate(body.find_all("div", class_="card-text-attack")[:2]):
        info_p = atk_div.find("p", class_="card-text-attack-info")
        cost_span = info_p.find("span", class_="ptcg-symbol")
        cost = cost_span.text.strip() if cost_span else None
        info_text = clean_text(info_p.text.replace(cost or "", "", 1))
        dmg_match = re.search(r"([\d+\-xX×]+)$", info_text)
        dmg_raw = dmg_match.group(1) if dmg_match else ""
        atk_name = clean_text(info_text[: info_text.rfind(dmg_raw)]) if dmg_raw else info_text
        effect_p = atk_div.find("p", class_="card-text-attack-effect")

        attacks[str(i + 1)] = {
            "cost": cost or None,
            "name": atk_name or None,
            "damage": to_int(dmg_raw),
            "effect": clean_text(effect_p.text) if effect_p else None,
        }

    return {
        "number": card_number,
        "name": name,
        "hp": hp,
        "type": card_type,
        "subtype": subtype,
        "card_text": card_text,
        "image": image,
        "rarity": rarity,
        "ex": ex,
        "mega": mega,
        "points": points,
        "pack": pack,
        "artist": artist,
        "stage": stage,
        "evolves_from": evolves_from,
        "retreat": retreat,
        "weakness": weakness,
        "ability": ability,
        "attacks": attacks,
        "raw_text": raw_text,
    }


def scrape_cards(set_code):
    """Scrape all cards in a set, stopping after MAX_CONSECUTIVE_ERRORS misses."""
    cards, errors, i = [], 0, 0

    while errors < MAX_CONSECUTIVE_ERRORS:
        i += 1
        try:
            cards.append(extract_card(fetch_page(f"{BASE_URL}{set_code}/{i}"), set_code))
            errors = 0
            if len(cards) % 10 == 0:
                print(f"    ...scraped {len(cards)} cards")
            time.sleep(0.15)
        except NotFound:
            errors += 1
        except Exception as e:  # network hiccup or layout change
            errors += 1
            print(f"    WARNING: card {i} failed: {type(e).__name__}: {e}")

    return cards

# ---------------------------------------------------------------------------
# Step 3: Transform scraped data into the card database format
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Step 4: Download card images
# ---------------------------------------------------------------------------
def download_images(cards, prefix):
    webp_dir, png_dir = os.path.join(ROOT_DIR, "images", "webp", "cards", prefix), os.path.join(ROOT_DIR, "images", "png", "cards", prefix)
    os.makedirs(webp_dir, exist_ok=True); os.makedirs(png_dir, exist_ok=True)

    total = len(cards)
    processed = 0

    for card in cards:
        source_url = card.pop("source_url", None)
        processed += 1

        if source_url and "limitlesstcg" in source_url:
            num = card["id"].split("-")[-1]
            out_webp, out_png = os.path.join(webp_dir, f"{num}.webp"), os.path.join(png_dir, f"{num}.png")

            if not (os.path.exists(out_webp) and os.path.exists(out_png)):
                try:
                    time.sleep(0.15)
                    img = Image.open(io.BytesIO(SESSION.get(source_url, timeout=30).content)).convert("RGBA")
                    img.save(out_webp, "WEBP"); img.save(out_png, "PNG")
                except Exception as e:
                    print(f"    Failed {card['id']}: {e}")

        if processed % 10 == 0 or processed == total:
            print(f"    ...processed {processed}/{total} images")



# ---------------------------------------------------------------------------
# Step 5: Download pack images from serebii.net
# ---------------------------------------------------------------------------
def slugify(name):
    """Convert a name to a filesystem-safe slug (lowercase, alphanumeric only)."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def serebii_slug(name):
    """Convert a name to a serebii URL slug (lowercase, keep hyphens only)."""
    return re.sub(r"[^a-z0-9-]", "", name.lower())


def download_pack_images(expansion_name, packs):
    webp_dir, png_dir = os.path.join(ROOT_DIR, "images", "webp", "packs"), os.path.join(ROOT_DIR, "images", "png", "packs")
    os.makedirs(webp_dir, exist_ok=True); os.makedirs(png_dir, exist_ok=True)
    exp_slug = serebii_slug(expansion_name)

    for pack in packs:
        out_webp, out_png = os.path.join(webp_dir, f"{pack['id']}.webp"), os.path.join(png_dir, f"{pack['id']}.png")
        if os.path.exists(out_webp) and os.path.exists(out_png): continue

        for ext in ("jpg", "png"):
            try:
                resp = SESSION.get(f"{SEREBII_BASE_URL}{exp_slug}/{serebii_slug(pack['name'])}.{ext}", timeout=15)
                if resp.status_code == 200 and len(resp.content) > 500:
                    img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                    img.save(out_webp, "WEBP"); img.save(out_png, "PNG")
                    break
            except Exception: continue

# ---------------------------------------------------------------------------
# Step 6: Update the current card database and expansions.json
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Add a new Pokemon TCG Pocket expansion")
    parser.add_argument("set_code", help="Set code from Limitless TCG (e.g. B3b, A1, PA, PB)")
    parser.add_argument("--name", help="Override expansion name (auto-detected if omitted)")
    parser.add_argument("--skip-images", action="store_true", help="Skip downloading card images")
    args = parser.parse_args()

    set_code = normalise_set_code(args.set_code)
    prefix = set_code_to_prefix(set_code)
    is_promo = set_code.startswith("P-")

    print(f"\n{'=' * 60}")
    print(f"  {'Updating promo set' if is_promo else 'Adding expansion'}: {set_code}")
    print(f"{'=' * 60}")

    # Step 1 ----------------------------------------------------------------
    print(f"\n[1/6] Discovering expansion info...")
    expansion_name, release_date = discover_set(set_code)
    if args.name:
        expansion_name = args.name
        print(f"    Using provided name: {expansion_name}")
    print(f"    {expansion_name} ({set_code}) -> prefix '{prefix}', released {release_date}")

    # Step 2 ----------------------------------------------------------------
    print(f"\n[2/6] Scraping cards from Limitless TCG...")
    raw_cards = scrape_cards(set_code)
    if not raw_cards:
        print("    ERROR: No cards found. Check the set code and try again.")
        sys.exit(1)
    print(f"    Scraped {len(raw_cards)} cards")

    # Step 3 ----------------------------------------------------------------
    print(f"\n[3/6] Transforming card data...")
    cards = transform_cards(raw_cards, set_code, expansion_name, release_date)
    pack_names = sorted({c["pack"] for c in cards})
    print(f"    {len(cards)} cards, packs: {', '.join(pack_names)}")

    # Step 4 ----------------------------------------------------------------
    if not args.skip_images:
        print(f"\n[4/6] Downloading card images...")
        download_images(cards, prefix)
    else:
        print(f"\n[4/6] Skipping image download (--skip-images)")
        for card in cards: card.pop("source_url", None)

    # Step 5 ----------------------------------------------------------------
    print(f"\n[5/6] Updating database files...")
    added = update_cards(cards, CURRENT_VERSION)
    if is_promo:
        print("    Promo set -- expansion entry already exists, skipping")
        expansion_packs = None
    else:
        expansion_packs = update_expansions(set_code, expansion_name, cards)

    # Step 6 ----------------------------------------------------------------
    if not args.skip_images and expansion_packs:
        print(f"\n[6/6] Downloading pack images...")
        download_pack_images(expansion_name, expansion_packs)
    else:
        print(f"\n[6/6] Skipping pack image download")

    print(f"\n{'=' * 60}")
    print(f"  Done! {expansion_name} ({set_code})")
    print(f"  {len(cards)} cards scraped, {added} new added to v{CURRENT_VERSION}.json")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()