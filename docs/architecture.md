# Architecture and design

## Data scraping and normalisation
[Limitless TCG](https://pocket.limitlesstcg.com/) formats its web pages for people. The scraper extracts the HTML and converts the text into structured data. It strips out whitespace and casts strings to integers for fields like health and attack damage. It converts text flags into standard boolean values.

## Constants and utilities
The [constants.py](../scripts/constants.py) file stores global configuration data: base URLs, valid energy types, pack point costs, and the dictionary of species names used for tag matching.
The [utils.py](../scripts/utils.py) module handles routine text operations. It normalises set codes, strips trailing whitespace, formats dates, and compiles the regular expressions used to identify special Pokémon.

## Data transformation
The [transformer.py](../scripts/transformer.py) script shapes the raw scraped dictionaries into the final JSON schema. It determines the correct `art_style` based on rarity and card type, and builds the `alternate_versions` array by reading the other prints listed on the [Limitless card page](https://pocket.limitlesstcg.com/).

The transformer also handles backwards compatibility. If the user specifies `v4` mode, the script passes the compiled `V5` object through a downgrade function. This strips out arrays and objects, reintroduces string-based "Yes" and "No" flags, and outputs the legacy flat dictionary.

## Special tags
The game uses mechanical tags like Ancient or Ultra Beast. [Limitless](https://pocket.limitlesstcg.com/) does not print these directly on the page. The [transformer](../scripts/transformer.py) uses the hardcoded lists of Pokémon species from [constants.py](../scripts/constants.py) to catch these. It evaluates card names against boundary-aware regular expressions to prevent false matches on substrings. It saves any matches to the JSON.

## Deck builder numbers and asset dependencies
The game client uses an internal integer, the deck builder number, to load decks and generate share codes. It is hidden inside the game's image filenames.

[Limitless](https://pocket.limitlesstcg.com/) sorts cards by their printed set numbers, which are entirely different. To bridge this gap, the pipeline downloads the latest release of the **[pokemon-tcg-pocket-database](https://github.com/flibustier/pokemon-tcg-pocket-database)** repository (maintained by [flibustier](https://github.com/flibustier)) and maps the datamined image filenames to their integers, publishing the result as `deckBuilderNr`.

That download is cached for the process and fails loudly if it comes back empty. An empty lookup would write `deckBuilderNr: 0` for every card, which passes both the schema and the tests, so a transient network error would otherwise poison the dataset with no visible symptom.

### Share codes are not published yet
[deck_code.py](../scripts/deck_code.py) implements the reverse-engineered binary layout and `base64` encoding, and its output is verified against known-good codes in the test suite. It is **not** wired into the transformer, so no card carries a `share_code` field today. Consumers that need one can build it themselves from `deckBuilderNr` using `create_deck_code`.