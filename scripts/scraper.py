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
r"""Scrape Pokemon TCG Pocket card data from the Limitless TCG website.

This module fetches and parses individual card pages from
``https://pocket.limitlesstcg.com/cards/``, extracting name, HP, type,
attacks, ability, rarity, pack, artist, and alternate print versions.
It also discovers set metadata (name and release date) from the index
page and iterates over sequential card numbers to scrape an entire set.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from constants import BASE_URL, MAX_CONSECUTIVE_ERRORS, MAX_RETRIES, PROMO_A_PACK_KEYWORDS, SESSION, DEFAULT_TIMEOUT, RATE_LIMIT_DELAY
from utils import clean_text, parse_release_date, parse_trainer_subtype, to_int

class NotFound(Exception):
    r"""NotFound

    Raised when a card page returns HTTP 404. The card does not exist,
    so the scraper should not retry it.
    """
    pass


def fetch_page(url):
    r"""fetch_page(url) -> BeautifulSoup

    Fetch a URL and return a parsed BeautifulSoup object. Retries on
    network errors up to ``MAX_RETRIES`` times with ``RATE_LIMIT_DELAY``
    seconds between attempts. Raises :class:`NotFound` immediately on
    HTTP 404 since a missing card is not a transient error.

    Args:
        url (str): the full URL to fetch

    Returns:
        BeautifulSoup: parsed HTML of the page

    Raises:
        NotFound: if the server returns HTTP 404
        requests.RequestException: if all retry attempts fail with a
            network or server error

    Example::

        >>> soup = fetch_page("https://pocket.limitlesstcg.com/cards/a1/1")
        >>> soup.find("title").text
        'Bulbasaur - Genetic Apex (A1) - PTCGP'
    """
    retry_delay = RATE_LIMIT_DELAY
    for attempt in range(MAX_RETRIES):
        try:
            response = SESSION.get(url, timeout=DEFAULT_TIMEOUT)
            if response.status_code == requests.codes.not_found:
                raise NotFound(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(retry_delay)
            retry_delay += RATE_LIMIT_DELAY
    raise ValueError("We're experiencing a network or server error. Retry later.")


def get_all_set_codes():
    r"""get_all_set_codes() -> list of str

    Fetch the card index page and return every set code listed in the
    sets table, uppercased.

    Returns:
        list of str: set codes such as ``"A1"``, ``"A2a"``, ``"P-A"``

    Example::

        >>> codes = get_all_set_codes()
        >>> "A1" in codes
        True
    """
    return [span.text.strip().upper() for span in fetch_page(BASE_URL).select("table.sets-table span.code")]


def discover_set(set_code):
    r"""discover_set(set_code) -> tuple

    Look up a set's display name and release date from the card index
    table. If the set is not listed on the index page yet, falls back
    to scraping the set page's ``<title>`` tag for the name. The
    release date is ``None`` in that case because the set page does
    not show one.

    Args:
        set_code (str): the set code to look up, case-insensitive
            (e.g. ``"a1"``, ``"p-a"``)

    Returns:
        tuple: ``(name, release_date)`` where name is a str and
        release_date is a str in ``"YYYY-MM-DD"`` format, or None if
        the set is not yet indexed

    Example::

        >>> name, date = discover_set("a1")
        >>> name
        'Genetic Apex'
        >>> date
        '2024-10-30'
    """
    for row in fetch_page(BASE_URL).select("table.sets-table tr"):
        code_el = row.find("span", class_="code")
        if not code_el or code_el.text.strip().lower() != set_code.lower(): continue
        cells = row.find_all("td")
        code_el.extract()
        return clean_text(cells[0].get_text(" ", strip=True)), parse_release_date(cells[1].get_text())
    # not indexed yet: fall back to the set page title, no date
    title = fetch_page(f"{BASE_URL}{set_code}").find("title").text
    return clean_text(title.split(" (")[0].split(" - ")[0]), None


def extract_card(soup, set_code=""):
    r"""extract_card(soup, set_code='') -> dict

    Parse a single card page and return a dictionary with every card
    attribute needed for the output JSON.

    The function reads the ``card-text`` div for name, HP, energy type,
    attacks, ability, and flavour text. It reads the rarity table for
    the current print's rarity and any alternate versions. It reads the
    ``card-prints-current`` div for the pack the card appears in. For
    Pokemon cards it also extracts stage, evolution source, retreat
    cost, and weakness from the type line and raw body text.

    For trainer cards, ``hp``, ``stage``, ``evolves_from``, ``retreat``,
    and ``weakness`` are all None. The ``card_text`` field holds the
    trainer's effect text; for Pokemon this is None.

    Args:
        soup (BeautifulSoup): parsed HTML of the card page
        set_code (str): the set code this card belongs to. Used to
            resolve pack keywords for promo sets (``"P-A"``).
            Default: ``""``

    Returns:
        dict: card data with the following keys:

        - ``number`` (str): card number within the set
        - ``name`` (str): card name
        - ``hp`` (int or None): hit points, or None for trainers
        - ``type`` (str): ``"Pokemon"`` or ``"Trainer"``
        - ``subtype`` (str or None): energy type for Pokemon,
          trainer subtype for trainers
        - ``card_text`` (str or None): trainer effect text,
          None for Pokemon
        - ``flavour_text`` (str or None): flavour text if present
        - ``image`` (str or None): URL of the card image
        - ``rarity`` (str or None): rarity symbol of the current print
        - ``alternate_versions`` (list of dict): other prints of this
          card. Each dict has ``set_code``, ``set_name``, ``id``,
          and ``rarity``.
        - ``ex`` (bool): whether the card is a Pokemon ex
        - ``mega`` (bool): whether the card is a Mega Evolution
        - ``points`` (int or None): prize points when knocked out
          (1, 2, or 3). None for trainers.
        - ``pack`` (str): pack the card appears in
        - ``artist`` (str or None): illustrator name
        - ``stage`` (str or None): ``"Basic"``, ``"Stage 1"``,
          ``"Stage 2"``, or None for trainers
        - ``evolves_from`` (str or None): name of the pre-evolution
        - ``retreat`` (int or None): retreat cost, None for trainers
        - ``weakness`` (str or None): weakness type, None for trainers
        - ``ability`` (dict): ``{"exists": bool, "name": str or None,
          "effect": str or None}``
        - ``attacks`` (dict): keys ``"1"`` and ``"2"``, each mapping
          to ``{"cost": str or None, "name": str or None,
          "damage": int or None, "effect": str or None}``
        - ``raw_text`` (str): full text of the card body. Used later
          by :func:`transform_cards` to detect parallel foil prints.

    .. note::

        The ``attacks`` dict always has both ``"1"`` and ``"2"`` keys.
        If a card has only one attack, the second entry stays filled
        with None values.

    Example::

        >>> soup = fetch_page("https://pocket.limitlesstcg.com/cards/a1/1")
        >>> card = extract_card(soup, "a1")
        >>> card["name"]
        'Bulbasaur'
        >>> card["hp"]
        70
        >>> card["attacks"]["1"]["name"]
        'Vine Whip'
    """
    body = soup.find("div", class_="card-text")
    title_el = body.find("p", class_="card-text-title")
    card_number = title_el.find("a")["href"].split("/")[-1]
    name = clean_text(title_el.find("a").text)

    # Title format: "Caterpie - Grass - 40 HP". Trainers omit energy and HP,
    # so len(title_parts) is 2 (name + "Trainer") instead of 3.
    title_parts = [p.strip() for p in title_el.get_text(" ", strip=True).split(" - ")]
    energy_type = title_parts[1] if len(title_parts) > 2 else None

    type_text_raw = body.find("p", class_="card-text-type").get_text(" ", strip=True)

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

    flavour_div = body.find("div", class_="card-text-flavor")
    flavour_text = clean_text(flavour_div.text) if flavour_div else None

    image_div = soup.find("div", class_="card-image")
    image = image_div.find("img")["src"] if image_div and image_div.find("img") else None

    rarity = None
    alt_versions = []
    rarity_table = soup.find("table", class_="card-prints-versions")
    if rarity_table:
        current = rarity_table.find("tr", class_="current")
        if current:
            rarity = clean_text(current.find_all("td")[-1].text)

        for row in rarity_table.find_all("tr")[1:]:
            tds = row.find_all("td")
            if not tds or not tds[0].find("a"): continue

            a_tag = tds[0].find("a")

            href = a_tag.get("href", "")
            c_set = [p for p in href.split("/") if p][-2].lower() if href else set_code.lower()
            c_num = clean_text(a_tag.find("span").text).replace("#", "") if a_tag.find("span") else ""

            alt_versions.append({
                "set_code": c_set,
                "set_name": clean_text(a_tag.contents[0]),
                "id": to_int(c_num),
                "rarity": clean_text(tds[1].text) or "Promo"
            })

    pack = "Every pack"
    set_info = soup.find("div", class_="card-prints-current")
    if set_info:
        if set_code == "P-A":
            for kw in PROMO_A_PACK_KEYWORDS:
                if kw in set_info.get_text(): pack = kw
        else:
            spans = set_info.find_all("span")
            if spans and spans[-1].text.strip().split("·")[-1].strip().endswith(" pack"):
                pack = spans[-1].text.strip().split("·")[-1].strip()
    pack = clean_text(pack)

    artist_div = body.find("div", class_="card-text-artist")
    artist = clean_text(artist_div.find("a").text) if artist_div and artist_div.find("a") else None

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
        weakness = weakness_match.group(1) if weakness_match else None

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
            "effect": (clean_text(effect_p.text) if effect_p else None) or None,

        }

    return {
        "number": card_number,
        "name": name,
        "hp": hp,
        "type": card_type,
        "subtype": subtype,
        "card_text": card_text,
        "flavour_text": flavour_text,
        "image": image,
        "rarity": rarity,
        "alternate_versions": alt_versions,
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
    r"""scrape_cards(set_code) -> list of dict

    Scrape every card in a set by requesting sequential card numbers
    starting at 1. Stops after ``MAX_CONSECUTIVE_ERRORS`` cards in a
    row return 404, which signals the end of the set. Non-404 errors
    are logged to stderr via ``tqdm.write`` and also count toward the
    consecutive error limit.

    Each successfully scraped card is the dict returned by
    :func:`extract_card`. Cards are returned in card-number order.

    Args:
        set_code (str): the set code to scrape (e.g. ``"a1"``,
            ``"p-a"``)

    Returns:
        list of dict: one card dict per card found, in ascending
        card-number order

    Example::

        >>> cards = scrape_cards("a1")
        >>> len(cards)
        286
        >>> cards[0]["name"]
        'Bulbasaur'
    """
    cards, errors, i = [], 0, 0
    with tqdm(desc=f"Scraping {set_code}", unit=" cards") as pbar:
        while errors < MAX_CONSECUTIVE_ERRORS:
            i += 1
            try:
                cards.append(extract_card(fetch_page(f"{BASE_URL}{set_code}/{i}"), set_code))
                errors = 0
                pbar.update(1)
                time.sleep(RATE_LIMIT_DELAY)
            except NotFound:
                errors += 1
            except Exception as e:
                errors += 1
                tqdm.write(f"WARNING: card {i} failed: {type(e).__name__}: {e}")
    return cards