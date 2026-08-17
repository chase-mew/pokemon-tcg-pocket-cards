import os
import sys
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "scripts"))  # constants.py, no package needed

from constants import CARDS_JSON_PATH, EXPANSIONS_JSON_PATH, V4_JSON_PATH
from tests.utils import _load

@pytest.fixture(scope="session")
def cards():
    return _load(CARDS_JSON_PATH)


@pytest.fixture(scope="session")
def v4_cards():
    path = V4_JSON_PATH if os.path.exists(V4_JSON_PATH) else V4_JSON_PATH.replace(".json", ".min.json")
    return _load(path)


@pytest.fixture(scope="session")
def expansions():
    return _load(EXPANSIONS_JSON_PATH)


@pytest.fixture(scope="session")
def by_set(cards):
    """{set: [cards in file order]}"""
    grouped = {}
    for card in cards:
        grouped.setdefault(card["set_code"], []).append(card)
    return grouped