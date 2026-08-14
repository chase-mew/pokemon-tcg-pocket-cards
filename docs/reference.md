# Technical Reference

## V5 Schema

The **[V5](../v5.json)** dataset is an array of card objects. Every card contains 31 fields.

| Field                | Type    | Description                                                                                      |
|:---------------------|:--------|:-------------------------------------------------------------------------------------------------|
| `id`                 | string  | Set prefix and padded card number (e.g., "a1-001").                                              |
| `name`               | string  | The printed name of the card.                                                                    |
| `set_code`           | string  | The normalised lowercase set code.                                                               |
| `set_name`           | string  | The full name of the expansion.                                                                  |
| `pack`               | string  | The specific pack the card drops from, or "Shared".                                              |
| `release_date`       | string  | ISO 8601 formatted release date. Null for promos.                                                |
| `type`               | string  | "Pokémon" or "Trainer".                                                                          |
| `subtype`            | string  | Energy type for Pokémon. Item classification for Trainers.                                       |
| `stage`              | string  | Basic, Stage 1, or Stage 2. Null for Trainers.                                                   |
| `evolves_from`       | string  | The name of the required pre-evolution Pokémon.                                                  |
| `rarity`             | string  | The visual rarity indicator.                                                                     |
| `pack_points`        | integer | The cost to craft the card. Null for promos.                                                     |
| `ex`                 | boolean | True if the card is an "ex" rulebox Pokémon.                                                     |
| `mega`               | boolean | True if the card is a Mega Evolution.                                                            |
| `shiny`              | boolean | True if the card depicts a shiny variant.                                                        |
| `special_tags`       | array   | Tags like "ancient", "future", or "ultra_beasts". Defaults to null.                              |
| `art_style`          | string  | The visual treatment category.                                                                   |
| `health`             | integer | The maximum hit points. Null for Trainers.                                                       |
| `retreat`            | integer | The energy cost to retreat. Null for Trainers.                                                   |
| `weakness`           | string  | The energy type the Pokémon is weak to.                                                          |
| `ability`            | object  | Contains `exists` (boolean), `name` (string), and `effect` (string).                             |
| `card_text`          | string  | The mechanical rules text for Trainer cards.                                                     |
| `flavour_text`       | string  | The lore text printed on the card.                                                               |
| `attacks`            | object  | Contains keys `1` and `2`. Each holds `cost`, `name`, `damage` (integer), and `effect` (string). |
| `points`             | integer | Points awarded to the opponent when knocked out (1, 2, or 3).                                    |
| `deckBuilderNr`      | integer | The internal integer used by the game client for deck rendering.                                 |
| `share_code`         | string  | The base64 encoded binary string for sharing the card in-game.                                   |
| `alternate_versions` | array   | Prints from other sets mapping `set_code`, `set_name`, `id`, and `rarity`.                       |
| `artist`             | string  | The credited illustrator.                                                                        |
| `image`              | string  | URL to the WEBP version of the card image.                                                       |
| `image_png`          | string  | URL to the PNG version of the card image.                                                        |
| `source_url`†        | string  | The external image link (stripped during the build process, not included in the final schema)    |


## V4 Schema

The **[V4](../v4.json)** schema is a legacy flat structure. It lacks arrays and objects.

| Field     | Type   | Description                                   |
|:----------|:-------|:----------------------------------------------|
| `id`      | string | Set prefix and padded card number.            |
| `name`    | string | The printed name of the card.                 |
| `rarity`  | string | The visual rarity indicator.                  |
| `pack`    | string | The specific pack the card drops from.        |
| `health`  | string | The maximum hit points. Empty string if none. |
| `image`   | string | URL to the PNG version of the card image.     |
| `fullart` | string | "Yes" or "No".                                |
| `ex`      | string | "Yes" or "No".                                |
| `artist`  | string | The credited illustrator.                     |
| `type`    | string | Energy type or Trainer classification.        |

## Command line arguments

The `add_expansion.py` script takes the following parameters:

| Argument	       | Description                                                                                      |   
|-----------------|--------------------------------------------------------------------------------------------------|
| `set_code`      | 	(Required) The set identifier or range string (e.g., `a1->b4`, `a1`, `pb`)                      |
| `--name`	       | (Optional) Forces a specific expansion name instead of auto-detecting it from the webpage title. |
| `--mode`        | (Optional) Sets the output format. Valid options are `v4` or `v5`. The default is `v5`.          |
| `--skip-images` | (Optional) Disables the downloading of WEBP and PNG image assets.                                |

## Test suite

The repository uses `pytest` to validate the JSON output. Run the test suite from the root directory.

```bash
pytest tests/
```

The tests cover:
- **Schema compliance:** ensures exact key order, strict null usage over empty strings, and valid data types.
- **Invariants:** verifies that sets are contiguous blocks, numbering has no gaps, and art styles follow the correct ordering (e.g., Full Arts precede Special Illustration Arts).
- **Cross-file consistency:** ensures every set in the JSON has a matching entry in the expansions file, and that pack names align exactly between the two files.
- **Image availability:** Checks that every scraped card has both a WEBP and PNG file present in the local [images/](../images) folder.