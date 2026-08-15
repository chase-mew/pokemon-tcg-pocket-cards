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

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os

BASE_URL = "https://pocket.limitlesstcg.com/cards/"
GITHUB_BASE_URL = (
    "https://raw.githubusercontent.com/chase-manning/"
    "pokemon-tcg-pocket-cards/refs/heads/main/images"
)
SEREBII_BASE_URL = "https://www.serebii.net/tcgpocket/"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = (
    "pokemon-tcg-pocket-cards/1.0 (+https://github.com/chase-manning/pokemon-tcg-pocket-cards)"
)
retries = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
SESSION.mount("https://", HTTPAdapter(max_retries=retries))
SESSION.mount("http://", HTTPAdapter(max_retries=retries))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
CURRENT_VERSION = 5
V1_JSON_PATH = os.path.join(ROOT_DIR, "v1.json")
V2_JSON_PATH = os.path.join(ROOT_DIR, "v2.json")
V3_JSON_PATH = os.path.join(ROOT_DIR, "v3.json")
V4_JSON_PATH = os.path.join(ROOT_DIR, "v4.json")
V5_DIR = os.path.join(ROOT_DIR, "data", "v5")
EXPANSIONS_JSON_PATH = os.path.join(V5_DIR, "expansions.json")
IMAGES_DIR = os.path.join(ROOT_DIR, "images")
WEBP_CARDS_DIR = os.path.join(IMAGES_DIR, "webp", "cards")
PNG_CARDS_DIR = os.path.join(IMAGES_DIR, "png", "cards")
WEBP_PACKS_DIR = os.path.join(IMAGES_DIR, "webp", "packs")
PNG_PACKS_DIR = os.path.join(IMAGES_DIR, "png", "packs")

ENERGY_TYPES = ("Grass", "Fire", "Water", "Lightning", "Psychic", "Fighting",
                "Darkness", "Metal", "Dragon", "Colorless")
STAGES = ("Basic", "Stage 1", "Stage 2")
RARITIES = ("◊", "◊◊", "◊◊◊", "◊◊◊◊", "☆", "☆☆", "☆☆☆", "Crown Rare", "Promo")
ART_STYLES = ("Illustration Art", "Full Art", "Special Illustration Art",
              "Immersive Art", "Shiny", "Shiny Full Art", "Parallel Foil")
PROMO_PREFIXES = ("pa", "pb")
FIRST_RELEASE = "2024-10-30"  # A1

PACK_POINTS = {"◊": 35, "◊◊": 70, "◊◊◊": 150, "◊◊◊◊": 500,
               "☆": 400, "☆☆": 1250, "☆☆☆": 1500, "♕": 2500, "Crown Rare": 2500}
SHINY_PACK_POINTS = {"☆": 1000, "☆☆": 1350, "☆☆☆": 1500}
TRAINER_SUBTYPES = ("Supporter", "Stadium", "Tool", "Item")

TAG_DEFINITIONS = {
    "ancient": [
        "Great Tusk", "Scream Tail", "Brute Bonnet", "Flutter Mane",
        "Slither Wing", "Sandy Shocks", "Roaring Moon", "Koraidon",
        "Walking Wake", "Gouging Fire", "Raging Bolt", "Sada", "Sada's"
    ],
    "future": [
        "Iron Treads", "Iron Bundle", "Iron Hands", "Iron Jugulis",
        "Iron Moth", "Iron Thorns", "Iron Valiant", "Miraidon",
        "Iron Leaves", "Iron Boulder", "Iron Crown", "Turo", "Turo's"
    ],
    "ultra_beasts": [
        "Nihilego", "Buzzwole", "Pheromosa", "Xurkitree", "Celesteela",
        "Kartana", "Guzzlord", "Poipole", "Naganadel", "Stakataka",
        "Blacephalon", "Dawn Wings Necrozma", "Dusk Mane Necrozma",
        "Necrozma", "Ultra Necrozma", "Lusamine", "Lusamine's"
    ]
}

MAX_CONSECUTIVE_ERRORS = 5      # missing cards in a row = end of set
MAX_RETRIES = 3                 # network retries per page

PROMO_A_PACK_KEYWORDS = [
    "Premium Missions",
    "Missions",
    "Shop",
    "Campaign",
    "Promo pack",
    "Wonder Pick",
]
PROMO_CARDS_PER_VOLUME = 5