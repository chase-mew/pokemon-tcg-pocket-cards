"""Bind the shared fixtures to the v4 dataset for everything under tests/legacy.

The root conftest resolves ``cards`` and ``expansions`` to data/v5. The
modules in this directory are the v4 suite, so they take the v4 files. A
subdirectory conftest shadows the parent only for tests beneath it, so the
v5 modules are unaffected.
"""
import json
import os

import pytest

from constants import V4_EXPANSIONS_JSON_PATH, V4_JSON_PATH


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def cards():
    path = V4_JSON_PATH if os.path.exists(V4_JSON_PATH) else V4_JSON_PATH.replace(".json", ".min.json")
    return _load(path)


@pytest.fixture(scope="session")
def expansions():
    return _load(V4_EXPANSIONS_JSON_PATH)
