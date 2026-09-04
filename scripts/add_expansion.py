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
r"""Add a new expansion to the Pokemon TCG Pocket cards database.

Scrapes card data from Limitless TCG, downloads card images, and
updates both the card database and ``expansions.json`` (the
expansion index). Main entry point for adding or updating sets.

Usage::

    python scripts/add_expansion.py B2b
    python scripts/add_expansion.py B1 --name "Mega Rising"
    python scripts/add_expansion.py PA              # update Promo-A with new cards
    python scripts/add_expansion.py PB --skip-images
    python scripts/add_expansion.py a1->b4           # process a range of sets
    python scripts/add_expansion.py --all            # scrape every known set

The script runs a six-step pipeline per set: discover metadata,
scrape raw card data, transform to the output schema, download card
images, update database files, and download pack images. After all
sets are processed, the v5 database is recompiled to sync alternate
version references across sets.
"""

import os
import jsonschema
import json
import argparse
import sys

from constants import CARDS_SCHEMA_PATH, CURRENT_VERSION
from database import update_cards, update_expansions, compile_v5_database
from downloader import download_images, download_pack_images
from scraper import discover_set, scrape_cards, get_all_set_codes
from transformer import downgrade_to_v4, strip_source_urls, transform_cards
from utils import normalise_set_code, set_code_to_prefix


def validate_schema(cards):
    r"""validate_schema(cards)

    Validate a list of card dicts against the v5 JSON schema at
    :data:`constants.CARDS_SCHEMA_PATH`. Prints a confirmation
    message on success and raises ``ValueError`` on failure with the
    JSON path and error message from the validator.

    The schema sets ``additionalProperties: false``, so this must run
    after ``source_url`` has been stripped from the cards, which
    happens at step 4 of :func:`process_single_set`.

    Args:
        cards (list of dict): transformed card dicts in v5 format,
            as produced by :func:`transform_cards.transform_cards`

    Raises:
        FileNotFoundError: if ``cards.schema.json`` does not exist
            in ``V5_DIR``
        ValueError: if one or more cards violate the schema. The
            error message includes the JSON path to the offending
            field and the validator's message.
    """
    schema_path = CARDS_SCHEMA_PATH
    if not os.path.exists(schema_path):
        raise FileNotFoundError(
            f"Required V5 schema not found: {schema_path}"
        )

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    try:
        jsonschema.validate(instance=cards, schema=schema)
        print("    Schema validation passed.")
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Schema violation in {e.json_path}: {e.message}")


def resolve_set_range(range_str):
    r"""resolve_set_range(range_str) -> list of str

    Parse a set code or range string and return a list of normalised
    set codes.

    A single code (no ``"->"``) is normalised and returned as a
    one-element list. A range like ``"a1->b4"`` is expanded to all
    set codes between the start and end, inclusive, using the set
    list fetched from the Limitless TCG index page.

    The index lists sets newest first. This function reverses that
    list so the range resolves oldest first, which is the order sets
    should be processed in.

    If the start code sorts after the end code in the reversed list,
    the two indices are swapped so the range still covers all sets
    between them.

    Args:
        range_str (str): a single set code (e.g. ``"B2b"``, ``"PA"``)
            or a range (e.g. ``"a1->b4"``)

    Returns:
        list of str: normalised set codes in chronological order

    Raises:
        SystemExit: if either the start or end code is not found in
            the index. Prints an error message before exiting.
    """
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
    r"""process_single_set(set_code, args)

    Run the full six-step pipeline for a single set:

    1. Discover: fetch the expansion name and release date from
       the Limitless TCG index page. If ``args.name`` is set, the
       provided name overrides the auto-detected one.
    2. Scrape: download every card page for the set from
       Limitless TCG and parse the raw card data.
    3. Transform: convert raw card dicts to the v5 schema. The
       v4 downgrade is deferred to step 5 because it drops
       ``source_url``, which step 4 needs.
    4. Download images: fetch card artwork from Limitless TCG
       and save in WebP and PNG format. Skipped if
       ``args.skip_images`` is set. Either way, ``source_url`` is
       stripped from every card afterwards.
    5. Update database: in v4 mode, downgrade the cards first; in
       v5 mode, validate against the JSON schema, which runs here
       rather than at step 3 because ``source_url`` is stripped at
       the end of step 4. Then merge into the appropriate JSON file
       (per-set for v5, single file for v4) and update the
       expansions index (v5 only).
    6. Download pack images: fetch pack artwork from Serebii.
       Skipped if ``args.skip_images`` is set or if no packs were
       produced (v4 mode).

    Progress messages are printed to stdout at each step. The
    function does not return a value; side effects are the downloaded
    images and updated JSON files on disk.

    Args:
        set_code (str): the set code to process, already normalised
            (e.g. ``"A1"``, ``"P-A"``, ``"B2b"``)
        args (argparse.Namespace): parsed CLI arguments. Must have
            ``name`` (str or None), ``mode`` (``"v4"`` or ``"v5"``),
            and ``skip_images`` (bool) attributes.
    """
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
    cards = transform_cards(raw_cards, set_code, expansion_name, "v5", release_date)
    pack_names = sorted({c["pack"] for c in cards})
    print(f"    {len(cards)} cards, packs: {', '.join(pack_names)}")

    # Step 4 ----------------------------------------------------------------
    if args.skip_images:
        print(f"\n[4/6] Skipping image download (--skip-images)")
    else:
        print(f"\n[4/6] Downloading card images...")
        download_images(cards, prefix)
    strip_source_urls(cards)

    # Step 5 ----------------------------------------------------------------
    print(f"\n[5/6] Updating database files...")
    if args.mode == "v4":
        cards = downgrade_to_v4(cards)
        target_version = 4
    else:
        validate_schema(cards)
        target_version = CURRENT_VERSION
    added = update_cards(cards, target_version)

    if args.mode == "v4":
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
    print(f"  {len(cards)} cards scraped, {added} new cards added")
    print(f"{'=' * 60}\n")


def main():
    r"""main()

    Parse command-line arguments and process one or more sets.

    Accepts a single set code, a range (``"a1->b4"``), or the
    ``--all`` flag to scrape every set listed on the Limitless TCG
    index page. Each set is processed via
    :func:`process_single_set`. After all sets are done, the v5
    database is recompiled via :func:`compile_v5_database` to sync
    alternate version references across sets.

    CLI arguments:

    - ``set_code`` (positional, optional): a set code or range.
      Required unless ``--all`` is given.
    - ``--all``: scrape every set on the index. The index lists them
      newest first, so the list is reversed and processed oldest
      first, which is the order the art-style state machine expects.
    - ``--name``: override the auto-detected expansion name. Cannot
      be used with ``--all``.
    - ``--mode``: output schema, ``"v4"`` or ``"v5"``. Default:
      ``"v5"``.
    - ``--skip-images``: skip downloading card and pack images.

    Raises:
        SystemExit: if no set code and no ``--all`` flag are
            provided, or if ``--all`` is combined with ``--name``.
    """
    parser = argparse.ArgumentParser(description="Add a new Pokemon TCG Pocket expansion")
    parser.add_argument("set_code", nargs="?", help="Set code or range (e.g. B3b, 'a1->b4', PA)")
    parser.add_argument("--all", action="store_true", help="Scrape all discoverable sets from Limitless")
    parser.add_argument("--name", help="Override expansion name (auto-detected if omitted)")
    parser.add_argument("--mode", choices=["v4", "v5"], default="v5", help="Target output schema format")
    parser.add_argument("--skip-images", action="store_true", help="Skip downloading card images")
    args = parser.parse_args()
    set_codes = []

    if args.all and args.name:
        parser.error("--name cannot be used with --all")
    elif args.all:
        set_codes = get_all_set_codes()
        set_codes.reverse()
    elif args.set_code:
        set_codes = resolve_set_range(args.set_code)
    else:
        print("Error: You must provide a set_code or use the --all flag.")
        sys.exit(1)

    for code in set_codes:
        process_single_set(code, args)

    if args.mode == "v5":
        print("\nCompiling v5 database and syncing alternate versions...")
        compile_v5_database()
        print("Compilation complete. Main v5 files generated.")



if __name__ == "__main__":
    main()