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
import io
import os
import time
from PIL import Image
from tqdm import tqdm
from constants import ROOT_DIR, SEREBII_BASE_URL, SESSION
from utils import serebii_slug

def download_images(cards, prefix):
    webp_dir, png_dir = os.path.join(ROOT_DIR, "images", "webp", "cards", prefix), os.path.join(ROOT_DIR, "images", "png", "cards", prefix)
    os.makedirs(webp_dir, exist_ok=True); os.makedirs(png_dir, exist_ok=True)

    for card in tqdm(cards, desc=f"Downloading {prefix} images", unit="img"):
        source_url = card.pop("source_url", None)

        if source_url and "limitlesstcg" in source_url:
            num = card["id"].split("-")[-1]
            out_webp = os.path.join(webp_dir, f"{num}.webp")
            out_png = os.path.join(png_dir, f"{num}.png")

            if not (os.path.exists(out_webp) and os.path.exists(out_png)):
                try:
                    time.sleep(0.15)
                    resp = SESSION.get(source_url, timeout=30)
                    resp.raise_for_status()
                    img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                    img.save(out_webp, "WEBP")
                    img.save(out_png, "PNG")
                except Exception as e:
                    raise RuntimeError(f"Critical failure downloading image for {card['id']}: {e}")

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