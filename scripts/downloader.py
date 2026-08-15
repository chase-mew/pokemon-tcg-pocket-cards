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
r"""Download card and pack artwork images.

Card images are fetched from the Limitless TCG website and saved in
both WebP and PNG formats. Pack images are fetched from Serebii.
Both functions skip files that already exist on disk.
"""

import io
import os
import time
from PIL import Image
from tqdm import tqdm
from constants import WEBP_CARDS_DIR, PNG_CARDS_DIR, WEBP_PACKS_DIR, PNG_PACKS_DIR, SEREBII_BASE_URL, SESSION, RATE_LIMIT_DELAY, IMAGE_TIMEOUT, DEFAULT_TIMEOUT
from urllib.parse import urlsplit
from utils import serebii_slug

def download_images(cards, prefix):
    r"""download_images(cards, prefix)

    Download card artwork from Limitless TCG and save each image in
    both WebP and PNG format. Images are fetched from the
    ``source_url`` field on each card dict, which must contain a URL
    from the ``limitlesstcg`` domain.

    For each card, the image number is extracted from the card ID
    (the part after the hyphen). The output files are written to
    ``WEBP_CARDS_DIR/{prefix}/{num}.webp`` and
    ``PNG_CARDS_DIR/{prefix}/{num}.png``. If both files already
    exist, the card is skipped.

    .. note::

        This function calls ``card.pop("source_url", None)`` on each
        card, removing the ``source_url`` key from the dict as a side
        effect. The source URL is only needed for downloading and is
        not part of the final JSON output.

    .. note::

        Any exception during download (network error, image decode
        failure, file write error) raises ``RuntimeError`` and halts
        the entire batch. This is intentional: a missing card image
        would break the downstream pipeline, so a partial download is
        worse than no download.

    Args:
        cards (list of dict): card dicts. Each must have an ``id``
            key (e.g. ``"a1-001"``) and a ``source_url`` key
            containing the Limitless TCG image URL. The
            ``source_url`` key is removed from each dict.
        prefix (str): the set prefix used for the output directory
            name (e.g. ``"a1"``)

    Raises:
        RuntimeError: if any image download or conversion fails. The
            error message includes the card ID and the underlying
            exception.
    """
    webp_dir, png_dir = os.path.join(WEBP_CARDS_DIR, prefix), os.path.join(PNG_CARDS_DIR, prefix)
    os.makedirs(webp_dir, exist_ok=True)
    os.makedirs(png_dir, exist_ok=True)

    for card in tqdm(cards, desc=f"Downloading {prefix} images", unit="img"):
        source_url = card.pop("source_url", None)
        num = card["id"].split("-")[-1]
        out_webp = os.path.join(webp_dir, f"{num}.webp")
        out_png = os.path.join(png_dir, f"{num}.png")

        if not (os.path.exists(out_webp) and os.path.exists(out_png)):
            parsed_url = urlsplit(source_url) if source_url else None
            hostname = parsed_url.hostname if parsed_url else None
            if (
                    parsed_url is None
                    or parsed_url.scheme != "https"
                    or not hostname
                    or (
                    hostname != "limitlesstcg.com"
                    and not hostname.endswith(".limitlesstcg.com")
            )
            ):
                raise RuntimeError(f"Missing or invalid source_url for {card['id']}")
            try:
                time.sleep(RATE_LIMIT_DELAY)
                resp = SESSION.get(source_url, timeout=IMAGE_TIMEOUT)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                img.save(out_webp, "WEBP")
                img.save(out_png, "PNG")
            except Exception as e:
                raise RuntimeError(f"Critical failure downloading image for {card['id']}: {e}")

def download_pack_images(expansion_name, packs):
    r"""download_pack_images(expansion_name, packs)

    Download pack artwork from Serebii and save each image in both
    WebP and PNG format. The Serebii URL is constructed from the
    expansion name and each pack's name, both converted to Serebii
    URL slugs. Both ``.jpg`` and ``.png`` extensions are tried in
    that order; the first response that returns HTTP 200 with more
    than 500 bytes of content is accepted.

    The 500-byte threshold filters out small placeholder or error
    images that Serebii may return for missing artwork.

    .. note::

        Errors are silently ignored. If neither extension produces a
        valid image, the pack is skipped without raising. This is
        less strict than :func:`download_images` because missing pack
        art is cosmetic, not a pipeline-breaking problem.

    Args:
        expansion_name (str): the expansion name, slugified for the
            Serebii URL path (e.g. ``"Genetic Apex"``)
        packs (list of dict): pack objects. Each must have an ``id``
            key (used for the output filename) and a ``name`` key
            (slugified for the Serebii URL). Pack objects are the ones
            returned by :func:`update_expansions` in db.py.
    """
    os.makedirs(WEBP_PACKS_DIR, exist_ok=True)
    os.makedirs(PNG_PACKS_DIR, exist_ok=True)
    exp_slug = serebii_slug(expansion_name)

    for pack in packs:
        out_webp, out_png = os.path.join(WEBP_PACKS_DIR, f"{pack['id']}.webp"), os.path.join(PNG_PACKS_DIR, f"{pack['id']}.png")
        if os.path.exists(out_webp) and os.path.exists(out_png):
            continue
        for ext in ("jpg", "png"):
            try:
                resp = SESSION.get(f"{SEREBII_BASE_URL}{exp_slug}/{serebii_slug(pack['name'])}.{ext}",
                                   timeout=DEFAULT_TIMEOUT)
                if resp.status_code == 200 and len(resp.content) > 500:
                    img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                    img.save(out_webp, "WEBP"); img.save(out_png, "PNG")
                    break
            except Exception: continue