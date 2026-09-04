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
r"""Resolve a raw set code once into everything the pipeline asks of it.

Before this existed, the scraper tested ``set_code == "P-A"``, the
transformer tested both that and ``set_code.startswith("P-")``, and the
database tested ``prefix in PROMO_PREFIXES``. Three spellings of one
question, keyed off two different representations of the same set.
"""

from dataclasses import dataclass

from utils import normalise_set_code, set_code_to_prefix


@dataclass(frozen=True)
class SetProfile:
    r"""A set code, normalised, with the questions the pipeline asks of it.

    Attributes:
        code (str): canonical set code, e.g. ``"A1"``, ``"P-A"``
        prefix (str): lowercase ID/path prefix, e.g. ``"a1"``, ``"pa"``
        is_promo (bool): a promo set (``P-A``, ``P-B``, ...)
        is_promo_a (bool): the Promo-A set specifically, which is the only
            one whose cards are grouped into numbered pack volumes
    """

    code: str
    prefix: str
    is_promo: bool
    is_promo_a: bool

    @classmethod
    def of(cls, raw_code):
        r"""of(raw_code) -> SetProfile

        Build a profile from a set code in any casing or spelling
        (``"pa"``, ``"PA"``, ``"P-A"`` all give the same result).
        """
        code = normalise_set_code(raw_code)
        return cls(code=code,
                   prefix=set_code_to_prefix(code),
                   is_promo=code.startswith("P-"),
                   is_promo_a=code == "P-A")
