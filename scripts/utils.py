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
import json
from datetime import datetime
from constants import TRAINER_SUBTYPES, TAG_DEFINITIONS

def clean_text(text):
    """Strip newlines, tabs, and duplicate spaces."""
    if not text:
        return None
    cleaned = re.sub(r'\s+', ' ', text).strip()
    return cleaned if cleaned else None

def normalise_set_code(code):
    """Normalise set code input (e.g. 'PA'/'pa' -> 'P-A', 'PB' -> 'P-B')."""
    c = code.strip().upper().replace("-", "")
    return f"P-{c[1]}" if len(c) == 2 and c[0] == 'P' else c

def _load_existing_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def set_code_to_prefix(set_code):
    """Convert set code to card ID prefix (e.g. 'B2b' -> 'b2b', 'P-A' -> 'pa')."""
    return f"p{set_code[2:].lower()}" if set_code.startswith("P-") else set_code.lower()

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

def slugify(name):
    """Convert a name to a filesystem-safe slug (lowercase, alphanumeric only)."""
    return re.sub(r"[^a-z0-9]", "", name.lower())

def serebii_slug(name):
    """Convert a name to a serebii URL slug (lowercase, keep hyphens only)."""
    return re.sub(r"[^a-z0-9-]", "", name.lower())

def compile_tag_matchers(tag_dict):
    return {tag: re.compile(rf"(?i)(?<![a-z0-9])(?:{'|'.join(map(re.escape, names))})(?![a-z0-9])") for tag, names in tag_dict.items()}