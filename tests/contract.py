"""The published card contract, read from the schema that defines it.

Four test modules used to carry byte-identical copies of this tuple. The
schema is the artifact consumers actually validate against, so it is the
source of truth; ``json.load`` preserves key order, so the published field
order comes along with it.
"""
from constants import CARDS_SCHEMA_PATH, V4_CARDS_SCHEMA_PATH
from tests.utils import _load

CARD_KEYS = tuple(_load(CARDS_SCHEMA_PATH)["items"]["properties"])
V4_CARD_KEYS = tuple(_load(V4_CARDS_SCHEMA_PATH)["items"]["properties"])
