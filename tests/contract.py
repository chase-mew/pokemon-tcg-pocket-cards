"""The published card contract, read from the schema that defines it.

Four test modules used to carry byte-identical copies of this tuple. The
schema is the artifact consumers actually validate against, so it is the
source of truth; ``json.load`` preserves key order, so the published field
order comes along with it.
"""
from constants import (CARDS_SCHEMA_PATH, V4_CARDS_SCHEMA_PATH,
                       V5_CORE_CARDS_SCHEMA_PATH, V5_CORE_NO_IMAGE_CARDS_SCHEMA_PATH,
                       V5_GAMEPLAY_CARDS_SCHEMA_PATH, V5_GAMEPLAY_NO_IMAGE_CARDS_SCHEMA_PATH,
                       V5_COLLECTION_CARDS_SCHEMA_PATH, V5_COLLECTION_NO_IMAGE_CARDS_SCHEMA_PATH)
from tests.utils import _load

CARD_KEYS = tuple(_load(CARDS_SCHEMA_PATH)["items"]["properties"])
V4_CARD_KEYS = tuple(_load(V4_CARDS_SCHEMA_PATH)["items"]["properties"])

CORE_KEYS = tuple(_load(V5_CORE_CARDS_SCHEMA_PATH)["items"]["properties"])
CORE_NO_IMAGE_KEYS = tuple(_load(V5_CORE_NO_IMAGE_CARDS_SCHEMA_PATH)["items"]["properties"])
GAMEPLAY_KEYS = tuple(_load(V5_GAMEPLAY_CARDS_SCHEMA_PATH)["items"]["properties"])
GAMEPLAY_NO_IMAGE_KEYS = tuple(_load(V5_GAMEPLAY_NO_IMAGE_CARDS_SCHEMA_PATH)["items"]["properties"])
COLLECTION_KEYS = tuple(_load(V5_COLLECTION_CARDS_SCHEMA_PATH)["items"]["properties"])
COLLECTION_NO_IMAGE_KEYS = tuple(_load(V5_COLLECTION_NO_IMAGE_CARDS_SCHEMA_PATH)["items"]["properties"])
