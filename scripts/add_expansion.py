#!/usr/bin/env python3
"""
Add a new expansion to the Pokemon TCG Pocket cards database.

Scrapes card data from Limitless TCG, downloads card images, and updates
both v4.json (card database) and expansions.json (expansion index).

Usage:
    python scripts/add_expansion.py B2b
    python scripts/add_expansion.py B1 --name "Mega Rising"
    python scripts/add_expansion.py PA              # update Promo-A with new cards
    python scripts/add_expansion.py PB --skip-images
"""

import argparse
import io
import json
import os
import random
import re
import sys
import time

import requests
from bs4 import BeautifulSoup
from PIL import Image


BASE_URL = "https://pocket.limitlesstcg.com/cards/"
GITHUB_BASE_URL = (
    "https://raw.githubusercontent.com/chase-manning/"
    "pokemon-tcg-pocket-cards/refs/heads/main/images"
)

SEREBII_BASE_URL = "https://www.serebii.net/tcgpocket/"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
V4_JSON_PATH = os.path.join(ROOT_DIR, "v4.json")
EXPANSIONS_JSON_PATH = os.path.join(ROOT_DIR, "expansions.json")
CARDS_DIR = os.path.join(ROOT_DIR, "images", "cards")
PACKS_DIR = os.path.join(ROOT_DIR, "images", "packs")

FULLART_RARITIES = ["☆", "☆☆", "☆☆☆", "Crown Rare"]
MAX_CONSECUTIVE_ERRORS = 5

PROMO_A_PACK_KEYWORDS = [
    "Premium Missions",
    "Missions",
    "Shop",
    "Campaign",
    "Promo pack",
    "Wonder Pick",
]
PROMO_CARDS_PER_VOLUME = 5


def normalize_set_code(code):
    """Normalize set code input (e.g. 'PA'/'pa' -> 'P-A', 'PB' -> 'P-B')."""
    cleaned = code.strip().upper().replace("-", "")
    if cleaned == "PA":
        return "P-A"
    if cleaned == "PB":
        return "P-B"
    return code.strip()


def fetch_page(url):
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(1)


def set_code_to_prefix(set_code):
    """Convert set code to card ID prefix (e.g. 'B2b' -> 'b2b', 'P-A' -> 'pa')."""
    if set_code.startswith("P-"):
        return f"p{set_code[2:].lower()}"
    return set_code.lower()


# ---------------------------------------------------------------------------
# Step 1: Discover expansion name from Limitless TCG
# ---------------------------------------------------------------------------


def discover_expansion(set_code):
    soup = fetch_page(f"{BASE_URL}{set_code}")
    title_tag = soup.find("title")
    if not title_tag:
        raise ValueError(f"Could not find page title for set {set_code}")
    title = title_tag.text
    # Regular: "Mega Shine (B2b) – Limitless TCG Pocket Database"
    # Promo:   "Promo-B – Limitless TCG Pocket Database"
    name = title.split(" (")[0].strip()
    for sep in (" – ", " — ", " - Limitless"):
        name = name.split(sep)[0].strip()
    return name


# ---------------------------------------------------------------------------
# Step 2: Scrape all cards
# ---------------------------------------------------------------------------


def extract_card(soup, set_code=""):
    """Extract the fields needed for v4.json from a single card page."""
    title_el = soup.find("p", class_="card-text-title")
    if not title_el or not title_el.find("a"):
        raise ValueError("Card title not found")

    card_number = title_el.find("a")["href"].split("/")[-1]
    name = title_el.find("a").text.strip()
    hp = re.sub(r"\D", "", title_el.text.split(" - ")[-1])

    title_text = title_el.text.strip()
    if " - " not in title_text:
        card_type = "Trainer"
    else:
        parts = title_text.split(" - ")
        extracted = parts[1].strip() if len(parts) >= 2 else "Unknown"
        card_type = "Trainer" if "HP" in extracted else extracted

    image_div = soup.find("div", class_="card-image")
    image = (
        image_div.find("img")["src"]
        if image_div and image_div.find("img")
        else ""
    )

    rarity = "Unknown"
    rarity_table = soup.find("table", class_="card-prints-versions")
    if rarity_table:
        current = rarity_table.find("tr", class_="current")
        if current:
            rarity = current.find_all("td")[-1].text.strip()
    fullart = "Yes" if rarity in FULLART_RARITIES else "No"

    ex = "Yes" if "ex" in name.split(" ") else "No"

    pack = "Every pack"
    set_info = soup.find("div", class_="card-prints-current")
    if set_info:
        if set_code == "P-A":
            text = set_info.get_text()
            for keyword in PROMO_A_PACK_KEYWORDS:
                if keyword in text:
                    pack = keyword
                    break
        else:
            spans = set_info.find_all("span")
            if spans:
                last_span_text = spans[-1].text.strip()
                segments = last_span_text.split("·")
                last_segment = segments[-1].strip()
                if last_segment.endswith(" pack"):
                    pack = last_segment

    artist_div = soup.find(
        "div", class_="card-text-section card-text-artist"
    )
    artist = (
        artist_div.find("a").text.strip()
        if artist_div and artist_div.find("a")
        else "Unknown"
    )

    return {
        "number": card_number,
        "name": name,
        "hp": hp,
        "type": card_type,
        "image": image,
        "rarity": rarity,
        "fullart": fullart,
        "ex": ex,
        "pack": pack,
        "artist": artist,
    }


def scrape_cards(set_code):
    """Scrape all cards in a set, stopping after consecutive 404s."""
    cards = []
    errors = 0
    i = 0

    while True:
        i += 1
        url = f"{BASE_URL}{set_code}/{i}"
        try:
            soup = fetch_page(url)
            card = extract_card(soup, set_code)
            cards.append(card)
            errors = 0
            if len(cards) % 10 == 0:
                print(f"    ...scraped {len(cards)} cards")
            time.sleep(0.15)
        except Exception:
            errors += 1
            if errors >= MAX_CONSECUTIVE_ERRORS:
                break

    return cards


# ---------------------------------------------------------------------------
# Step 3: Transform scraped data into v4.json format
# ---------------------------------------------------------------------------


def transform_cards(raw_cards, set_code, expansion_name):
    prefix = set_code_to_prefix(set_code)
    is_pa = set_code == "P-A"
    is_promo = set_code.startswith("P-")

    specific_packs = {
        c["pack"] for c in raw_cards if c["pack"] != "Every pack"
    }
    is_multi_pack = len(specific_packs) > 0

    promo_volume = 1
    promo_volume_count = 0

    transformed = []
    for card in raw_cards:
        card_id = f"{prefix}-{card['number'].zfill(3)}"

        rarity = card["rarity"]
        if rarity == "Crown Rare":
            rarity = "♕"
        if is_promo:
            rarity = "Promo"

        pack = card["pack"]
        if is_pa:
            if pack == "Promo pack":
                promo_volume_count += 1
                if promo_volume_count > PROMO_CARDS_PER_VOLUME:
                    promo_volume += 1
                    promo_volume_count = 1
                pack = f"Promo V{promo_volume}"
        elif is_promo:
            pack = expansion_name
        elif pack == "Every pack":
            pack = (
                f"Shared({expansion_name})"
                if is_multi_pack
                else expansion_name
            )
        elif pack.endswith(" pack"):
            pack = pack[:-5]

        transformed.append(
            {
                "id": card_id,
                "name": card["name"],
                "rarity": rarity,
                "pack": pack,
                "health": card["hp"],
                "image": card["image"],
                "fullart": card["fullart"],
                "ex": card["ex"],
                "artist": card["artist"],
                "type": card["type"],
            }
        )

    return transformed


# ---------------------------------------------------------------------------
# Step 4: Download card images
# ---------------------------------------------------------------------------


def download_images(cards):
    os.makedirs(CARDS_DIR, exist_ok=True)
    downloaded = 0
    skipped = 0
    failed = 0

    for card in cards:
        card_id = card["id"]
        source_url = card["image"]
        github_url = f"{GITHUB_BASE_URL}/cards/{card_id}.png"
        output_path = os.path.join(CARDS_DIR, f"{card_id}.png")

        if os.path.exists(output_path):
            card["image"] = github_url
            skipped += 1
            continue

        if "limitlesstcg" not in source_url:
            continue

        try:
            time.sleep(random.uniform(0.1, 0.4))
            response = requests.get(source_url, timeout=30)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content))
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            img.save(output_path, "PNG")
            card["image"] = github_url
            downloaded += 1
            if downloaded % 10 == 0:
                print(f"    ...downloaded {downloaded} images")
        except Exception as e:
            print(f"    Failed to download {card_id}: {e}")
            failed += 1

    print(f"    Downloaded {downloaded}, skipped {skipped} existing"
          + (f", {failed} failed" if failed else ""))


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
    os.makedirs(PACKS_DIR, exist_ok=True)
    exp_slug = serebii_slug(expansion_name)

    for pack in packs:
        pack_id = pack["id"]
        output_path = os.path.join(PACKS_DIR, f"{pack_id}.png")

        existing = False
        for ext in ("png", "jpg", "jpeg"):
            candidate_path = os.path.join(PACKS_DIR, f"{pack_id}.{ext}")
            if os.path.exists(candidate_path):
                print(f"    Pack image already exists: {pack_id} ({ext})")
                existing = True
                break
        if existing:
            continue

        pack_slug = serebii_slug(pack["name"])
        downloaded = False

        for ext in ("jpg", "png"):
            url = f"{SEREBII_BASE_URL}{exp_slug}/{pack_slug}.{ext}"
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200 and len(resp.content) > 500:
                    img = Image.open(io.BytesIO(resp.content))
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")
                    img.save(output_path, "PNG")
                    print(f"    Downloaded pack image: {pack_id}")
                    downloaded = True
                    break
            except Exception:
                continue

        if not downloaded:
            print(f"    Could not download pack image for {pack_id} "
                  f"(tried {SEREBII_BASE_URL}{exp_slug}/{pack_slug}.*)")


# ---------------------------------------------------------------------------
# Step 6: Update v4.json and expansions.json
# ---------------------------------------------------------------------------


def update_v4(new_cards):
    with open(V4_JSON_PATH, "r", encoding="utf-8") as f:
        existing = json.load(f)

    existing_ids = {c["id"] for c in existing}
    to_add = [c for c in new_cards if c["id"] not in existing_ids]

    if not to_add:
        print("    No new cards to add (all already exist)")
        return 0

    existing.extend(to_add)
    with open(V4_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"    Added {len(to_add)} cards (total now: {len(existing)})")
    return len(to_add)


def update_expansions(set_code, expansion_name, cards):
    prefix = set_code_to_prefix(set_code)

    with open(EXPANSIONS_JSON_PATH, "r", encoding="utf-8") as f:
        expansions = json.load(f)

    for exp in expansions:
        if exp["id"] == prefix:
            print(f"    Expansion '{prefix}' already in expansions.json")
            return exp["packs"]

    unique_packs = sorted(
        {c["pack"] for c in cards if not c["pack"].startswith("Shared(")}
    )

    if not unique_packs or unique_packs == [expansion_name]:
        packs = [
            {
                "id": f"{prefix}-booster",
                "name": "Booster",
                "image": f"{GITHUB_BASE_URL}/packs/{prefix}-booster.png",
            }
        ]
    else:
        packs = []
        for pack_name in unique_packs:
            slug = slugify(pack_name)
            packs.append(
                {
                    "id": f"{prefix}-{slug}",
                    "name": pack_name,
                    "image": f"{GITHUB_BASE_URL}/packs/{prefix}-{slug}.png",
                }
            )

    expansions.append(
        {"id": prefix, "name": expansion_name, "packs": packs}
    )

    with open(EXPANSIONS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(expansions, f, indent=2, ensure_ascii=False)

    pack_list = ", ".join(p["name"] for p in packs)
    print(f"    Added expansion '{expansion_name}' with packs: {pack_list}")
    return packs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Add a new Pokemon TCG Pocket expansion"
    )
    parser.add_argument(
        "set_code",
        help="Set code from Limitless TCG (e.g. B2b, A1, PA, PB)",
    )
    parser.add_argument(
        "--name", help="Override expansion name (auto-detected if omitted)"
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip downloading card images",
    )
    args = parser.parse_args()

    set_code = normalize_set_code(args.set_code)
    prefix = set_code_to_prefix(set_code)
    is_promo = set_code.startswith("P-")

    print(f"\n{'=' * 60}")
    if is_promo:
        print(f"  Updating promo set: {set_code}")
    else:
        print(f"  Adding expansion: {set_code}")
    print(f"{'=' * 60}")

    # Step 1 ----------------------------------------------------------------
    print(f"\n[1/6] Discovering expansion info...")
    if args.name:
        expansion_name = args.name
        print(f"    Using provided name: {expansion_name}")
    else:
        expansion_name = discover_expansion(set_code)
    print(f"    {expansion_name} ({set_code}) -> prefix '{prefix}'")

    # Step 2 ----------------------------------------------------------------
    print(f"\n[2/6] Scraping cards from Limitless TCG...")
    raw_cards = scrape_cards(set_code)
    if not raw_cards:
        print("    ERROR: No cards found. Check the set code and try again.")
        sys.exit(1)
    print(f"    Scraped {len(raw_cards)} cards")

    # Step 3 ----------------------------------------------------------------
    print(f"\n[3/6] Transforming card data...")
    cards = transform_cards(raw_cards, set_code, expansion_name)
    pack_names = sorted({c["pack"] for c in cards})
    print(f"    {len(cards)} cards, packs: {', '.join(pack_names)}")

    # Step 4 ----------------------------------------------------------------
    if not args.skip_images:
        print(f"\n[4/6] Downloading card images...")
        download_images(cards)
    else:
        print(f"\n[4/6] Skipping image download (--skip-images)")
        for card in cards:
            card["image"] = f"{GITHUB_BASE_URL}/cards/{card['id']}.png"

    # Step 5 ----------------------------------------------------------------
    print(f"\n[5/6] Updating database files...")
    added = update_v4(cards)
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
    print(f"  {len(cards)} cards scraped, {added} new cards added to v4.json")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
