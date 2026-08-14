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
from scraper import discover_set, scrape_cards, get_all_set_codes
from transformer import transform_cards
from utils import normalise_set_code, set_code_to_prefix


def resolve_set_range(range_str):
    if "->" not in range_str:
        return [normalise_set_code(range_str)]

    start_raw, end_raw = range_str.split("->")
    start_code = normalise_set_code(start_raw)
    end_code = normalise_set_code(end_raw)

    all_codes = [normalise_set_code(c) for c in get_all_set_codes()]
    all_codes.reverse()

    if start_code not in all_codes or end_code not in all_codes:
        print(f"Error: Could not find one of the sets in the range {start_code} to {end_code}.")
        sys.exit(1)

    start_idx = all_codes.index(start_code)
    end_idx = all_codes.index(end_code)

    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    return all_codes[start_idx:end_idx + 1]


def process_single_set(set_code, args):
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
    cards = transform_cards(raw_cards, set_code, expansion_name, args.mode, release_date)
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
    target_version = 4 if args.mode == "v4" else CURRENT_VERSION
    added = update_cards(cards, target_version)

    if is_promo or args.mode == "v4":
        print("    Skipping expansion index update")
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
    print(f"  {len(cards)} cards scraped, {added} new added to v{target_version}.json")
    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="Add a new Pokemon TCG Pocket expansion")
    parser.add_argument("set_code", help="Set code or range (e.g. B3b, a1->b4, PA)")
    parser.add_argument("--name", help="Override expansion name (auto-detected if omitted)")
    parser.add_argument("--mode", choices=["v4", "v5"], default="v5", help="Target output schema format")
    parser.add_argument("--skip-images", action="store_true", help="Skip downloading card images")
    args = parser.parse_args()

    set_codes = resolve_set_range(args.set_code)
    for code in set_codes:
        process_single_set(code, args)


if __name__ == "__main__":
    main()