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
r"""Small helper functions shared across the scraper and transformer.

Most of these are single-purpose text utilities: whitespace cleaning,
set-code normalisation, integer extraction, date parsing, slug
generation, and regex compilation for tag matching. Nothing here
makes network requests or does I/O except :func:`_load_existing_json`,
which reads a local file.
"""
import os
import re
import json
from datetime import datetime
from constants import TRAINER_SUBTYPES

def normalise_set_code(code):
    r"""normalise_set_code(code) -> str

    Normalise a set code to its canonical form. Two-letter codes
    starting with ``P`` are formatted as ``"P-X"`` (promo sets).
    All other codes are uppercased with hyphens removed.

    Args:
        code (str): raw set code, any case (e.g. ``"pa"``, ``"PA"``,
            ``"P-A"``, ``"a1"``)

    Returns:
        str: normalised code (e.g. ``"P-A"``, ``"A1"``)

    Example::

        >>> normalise_set_code("pa")
        'P-A'
        >>> normalise_set_code("a1")
        'A1'
        >>> normalise_set_code("P-A")
        'P-A'
    """
    c = code.strip().upper().replace("-", "")
    return f"P-{c[1]}" if len(c) == 2 and c[0] == 'P' else c


def clean_text(text):
    r"""clean_text(text) -> str or None

    Collapse runs of whitespace (newlines, tabs, multiple spaces) into
    a single space and strip leading and trailing whitespace. Returns
    None if the input is falsy or if nothing is left after cleaning.

    Args:
        text (str or None): the text to clean

    Returns:
        str or None: cleaned text, or None if the result would be empty

    Example::

        >>> clean_text("  Charizard\n  ex  ")
        'Charizard ex'
        >>> clean_text("   ") is None
        True
    """
    if not text:
        return None
    cleaned = re.sub(r'\s+', ' ', text).strip()
    return cleaned if cleaned else None


def _load_existing_json(filepath):
    r"""_load_existing_json(filepath) -> list or dict

    Read and parse a JSON file. Returns an empty list if the file
    does not exist, so callers can treat the result as an iterable
    without checking for None.

    Args:
        filepath (str): path to the JSON file

    Returns:
        list or dict: parsed JSON contents, or ``[]`` on
        ``FileNotFoundError``

    Raises:
        json.JSONDecodeError: if the file exists but contains
            invalid JSON
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def set_code_to_prefix(set_code):
    r"""set_code_to_prefix(set_code) -> str

    Convert a set code to the lowercase prefix used in card IDs and
    image directory names. Promo codes like ``"P-A"`` become ``"pa"``.
    Regular codes like ``"A1"`` become ``"a1"``.

    Args:
        set_code (str): the set code to convert

    Returns:
        str: lowercase prefix for card IDs and file paths

    Example::

        >>> set_code_to_prefix("P-A")
        'pa'
        >>> set_code_to_prefix("A1")
        'a1'
        >>> set_code_to_prefix("B2b")
        'b2b'
    """
    return f"p{set_code[2:].lower()}" if set_code.startswith("P-") else set_code.lower()

def to_int(text, default=None):
    r"""to_int(text, default=None) -> int or None

    Extract the first integer from a string. Useful for parsing
    values like ``"40 HP"`` (returns 40) or ``"100+"`` (returns 100).
    Returns the default if the input is None, empty, or contains no
    digits.

    Args:
        text (str or None): text to parse
        default (int or None): value to return if no digit is found.
            Default: ``None``

    Returns:
        int or None: the first integer in the text, or ``default``

    Example::

        >>> to_int("40 HP")
        40
        >>> to_int("100+")
        100
        >>> to_int("") is None
        True
        >>> to_int("", default=0)
        0
    """
    match = re.search(r"\d+", text or "")
    return int(match.group(0)) if match else default

def parse_release_date(text):
    r"""parse_release_date(text) -> str or None

    Parse a date in ``"DD Mon YY"`` format (as used on the Limitless
    TCG index page) and return it as an ISO ``"YYYY-MM-DD"`` string.
    Returns None for empty or None input, which is typical for promo
    sets that do not have a release date on the index.

    Args:
        text (str or None): date string like ``"30 Jun 26"``

    Returns:
        str or None: ISO date string (``"YYYY-MM-DD"``), or None if
        the input is blank

    Raises:
        ValueError: if the text is non-empty but does not match the
            expected ``"%d %b %y"`` format

    Example::

        >>> parse_release_date("30 Jun 26")
        '2026-06-30'
        >>> parse_release_date(None) is None
        True
        >>> parse_release_date("") is None
        True
    """
    text = (text or "").strip()
    return datetime.strptime(text, "%d %b %y").strftime("%Y-%m-%d") if text else None

def parse_trainer_subtype(type_text):
    r"""parse_trainer_subtype(type_text) -> str or None

    Extract the subtype from a trainer card's type line by checking
    for each known subtype in :data:`TRAINER_SUBTYPES`. Returns the
    first match, or None if none is found.

    Args:
        type_text (str): the type line text, e.g.
            ``"Trainer - Pokemon Tool"``

    Returns:
        str or None: one of ``"Supporter"``, ``"Stadium"``,
        ``"Tool"``, ``"Item"``, or None

    Example::

        >>> parse_trainer_subtype("Trainer - Pokemon Tool")
        'Tool'
        >>> parse_trainer_subtype("Trainer - Supporter")
        'Supporter'
    """
    return next((s for s in TRAINER_SUBTYPES if s in type_text), None)

def slugify(name):
    r"""slugify(name) -> str

    Convert a name to a filesystem-safe slug: lowercase, alphanumeric
    characters only. Everything else (spaces, punctuation, hyphens)
    is removed.

    Args:
        name (str): the name to slugify

    Returns:
        str: lowercase alphanumeric slug

    Example::

        >>> slugify("Mr. Mime")
        'mrmime'
        >>> slugify("Ho-Oh")
        'hooh'
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())

def serebii_slug(name):
    r"""serebii_slug(name) -> str

    Convert a name to a slug suitable for Serebii URLs: lowercase,
    alphanumeric, hyphen and apostrophe characters kept. Everything
    else (spaces, other punctuation) is removed. Unlike
    :func:`slugify`, this preserves hyphens and apostrophes, both of
    which Serebii keeps in its URL paths: it writes
    ``space-timesmackdown`` and ``teamrocket'sambition``, so dropping
    either character produces a 404.

    Args:
        name (str): the name to slugify

    Returns:
        str: lowercase slug with hyphens preserved

    Example::

        >>> serebii_slug("Ho-Oh")
        'ho-oh'
        >>> serebii_slug("Mr. Mime")
        'mrmime'
        >>> serebii_slug("Space-Time Smackdown")
        'space-timesmackdown'
        >>> serebii_slug("Team Rocket's Ambition")
        "teamrocket'sambition"
    """
    return re.sub(r"[^a-z0-9'-]", "", name.lower())

def compile_tag_matchers(tag_dict):
    r"""compile_tag_matchers(tag_dict) -> dict

    Compile a dictionary of tag definitions into a dictionary of
    compiled regex patterns. Each pattern matches any of the card
    names listed under that tag, case-insensitively, with word
    boundaries (no alphanumeric or digit on either side) to avoid
    partial matches like matching "Turo" inside "Turonator"
    (i know that's not its actual name, just bear with me for
    this future-proofing hypothetical)

    Args:
        tag_dict (dict): mapping of tag name to list of card names.
            Typically :data:`TAG_DEFINITIONS` from constants.

    Returns:
        dict: mapping of tag name to compiled :class:`re.Pattern`.
        Use ``pattern.search(card_name)`` to check if a card matches.

    Example::

        >>> matchers = compile_tag_matchers(
        ...     {"ancient": ["Great Tusk", "Roaring Moon"]})
        >>> bool(matchers["ancient"].search("Great Tusk ex"))
        True
        >>> bool(matchers["ancient"].search("Pikachu"))
        False
    """
    return {tag: re.compile(rf"(?i)(?<![a-z0-9])(?:{'|'.join(map(re.escape, names))})(?![a-z0-9])") for tag, names in tag_dict.items()}


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
