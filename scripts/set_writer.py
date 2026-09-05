# Copyright (C) 2024 Chase Manning <chase@manning.dev>
# Copyright (C) 2026 Leonid Dalin <infoLeonid@protonmail.com> & Chase Manning <chase@manning.dev>
#
# Original code by Chase Manning is released under the MIT License.
# Modifications and additions for version 5 onwards are released under
# the GNU Affero General Public License v3.0 (AGPL-3.0-or-later).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Adapters that own the v4 and v5 write sequences for a single set.

``process_single_set`` picks one adapter via :func:`writer_for` and
calls :meth:`write` once. Each mode knows its own validate -> write ->
validate shape; the orchestrator does not.
"""

import json
import os

import jsonschema

from constants import CARDS_SCHEMA_PATH, EXPANSIONS_JSON_PATH, EXPANSIONS_SCHEMA_PATH, V4_CARDS_SCHEMA_PATH
from database import append_to_v4, update_expansions, write_set_file
from transformer import downgrade_to_v4
from utils import _load_existing_json


def validate_schema(instance, schema_path=None, label="cards"):
    r"""validate_schema(instance, schema_path=CARDS_SCHEMA_PATH, label="cards")

    Validate ``instance`` against the JSON schema at ``schema_path``.

    Both v5 schemas set ``additionalProperties: false``, so this must
    run after :func:`transformer.strip_source_urls`.

    Args:
        instance: the parsed JSON to validate (a list of cards, or
            the expansion index)
        schema_path (str): path to the schema. Default:
            :data:`constants.CARDS_SCHEMA_PATH`
        label (str): what is being validated, used in messages

    Raises:
        FileNotFoundError: if the schema file does not exist
        ValueError: on a schema violation, naming the JSON path and
            message
    """
    if schema_path is None:
        schema_path = CARDS_SCHEMA_PATH

    if not os.path.exists(schema_path):
        raise FileNotFoundError(
            f"Required schema not found ({label}): {schema_path}"
        )

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    try:
        jsonschema.validate(instance=instance, schema=schema)
        print(f"    Schema validation passed ({label}).")
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Schema violation in {label} at {e.json_path}: {e.message}")


class V5Writer:
    """Write the v5 per-set file, the expansions index, and validate both."""

    def __init__(self, set_code, expansion_name):
        self._set_code = set_code
        self._expansion_name = expansion_name

    def write(self, cards):
        validate_schema(cards)
        added = write_set_file(cards)
        expansion_packs = update_expansions(self._set_code, self._expansion_name, cards)
        validate_schema(_load_existing_json(EXPANSIONS_JSON_PATH),
                        EXPANSIONS_SCHEMA_PATH, "expansions")
        return added, expansion_packs


class V4Writer:
    """Downgrade to the v4 schema, validate, and append to the v4 file."""

    def write(self, cards):
        v4_cards = downgrade_to_v4(cards)
        validate_schema(v4_cards, V4_CARDS_SCHEMA_PATH, "v4 cards")
        return append_to_v4(v4_cards), None


def writer_for(mode, set_code, expansion_name):
    """Return the writer for ``mode``; raise ``ValueError`` on anything else."""
    if mode == "v4":
        return V4Writer()
    if mode == "v5":
        return V5Writer(set_code, expansion_name)
    raise ValueError(f"unknown mode: {mode}")