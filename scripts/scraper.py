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
import time
import requests
from bs4 import BeautifulSoup

from constants import BASE_URL, MAX_CONSECUTIVE_ERRORS, MAX_RETRIES, PROMO_A_PACK_KEYWORDS, SESSION
from utils import clean_text, parse_release_date, parse_trainer_subtype, to_int

class NotFound(Exception):
    """Page returned 404. the card doesn't exist, don't retry."""
    pass

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

def discover_set(set_code):
    """(name, release_date) read from the /cards index table."""
    soup = fetch_page(BASE_URL)
    for row in soup.select("table.sets-table tr"):
        code_el = row.find("span", class_="code")
        if not code_el or code_el.text.strip().lower() != set_code.lower():
            continue
        cells = row.find_all("td")
        code_el.extract()
        return clean_text(cells[0].get_text(" ", strip=True)), parse_release_date(cells[1].get_text())
    # not indexed yet: fall back to the set page title, no date
    title = fetch_page(f"{BASE_URL}{set_code}").find("title").text
    return clean_text(title.split(" (")[0].split(" – ")[0]), None

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
        except Exception as e:
            errors += 1
            print(f"    WARNING: card {i} failed: {type(e).__name__}: {e}")
    return cards