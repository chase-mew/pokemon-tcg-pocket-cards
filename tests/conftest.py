import os
import sys
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "scripts"))  # constants.py, no package needed

from constants import EXPANSIONS_JSON_PATH, V4_JSON_PATH, V5_JSON_PATH, PNG_CARDS_DIR
from tests.utils import _load

@pytest.fixture(scope="session")
def cards():
    return _load(V5_JSON_PATH)


@pytest.fixture(scope="session")
def v4_cards():
    return _load(V4_JSON_PATH)


@pytest.fixture(scope="session")
def expansions():
    return _load(EXPANSIONS_JSON_PATH)


@pytest.fixture(scope="session")
def by_set(cards):
    """{set: [cards in file order]}"""
    grouped = {}
    for card in cards:
        grouped.setdefault(card["set"], []).append(card)
    return grouped


