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
import sys

from constants import CURRENT_VERSION
from database import update_cards, update_expansions
from downloader import download_images, download_pack_images
from scraper import discover_set, scrape_cards
from transformer import transform_cards
from utils import normalise_set_code, set_code_to_prefix

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