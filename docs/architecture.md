# Architecture and design

## Data scraping and normalisation
[Limitless TCG](https://pocket.limitlesstcg.com/) formats its web pages for people. The scraper extracts the HTML and converts the text into structured data. It strips out whitespace and casts strings to integers for fields like health and attack damage. It converts text flags into standard boolean values.

## Constants and utilities
The [constants.py](../scripts/constants.py) file stores global configuration data. This includes base URLs, valid energy types, pack point costs, and the dictionary of species names used for tag matching.    
The [utils.py](../scripts/utils.py) module handles routine text operations. It normalises set codes, strips trailing whitespace, formats dates, and compiles the regular expressions used to identify special Pokémon.

## Data transformation
The [transformer.py](../scripts/transformer.py) script shapes the raw scraped dictionaries into the final JSON schema. It determines the correct `art_style` based on a combination of rarity and card type. It builds the `alternate_versions` array by reading the other prints listed on the [Limitless card page](https://pocket.limitlesstcg.com/) 

The transformer also handles backwards compatibility. If the user specifies the `V4` mode, the script passes the compiled `V5` object through a downgrade function. This strips out the arrays and objects, reintroduces string based "Yes" and "No" flags, and outputs the legacy flat dictionary.

## Special tags
The game uses mechanical tags like Ancient or Ultra Beast. [Limitless](https://pocket.limitlesstcg.com/) does not print these directly on the page. The [transformer](../scripts/transformer.py) uses the hardcoded lists of Pokémon species from [constants.py](../scripts/constants.py) to catch these. It evaluates card names against boundary aware regular expressions to prevent false matches on substrings. It saves any matches to the JSON.

## Deck share codes and asset dependencies
The game client uses an internal integer called the deck builder number to load decks and generate share codes. This integer is hidden inside the game's image filenames. 

[Limitless](https://pocket.limitlesstcg.com/) sorts cards by their printed set numbers, which are entirely different. To bridge this gap, the pipeline downloads the latest release of the **[pokemon-tcg-pocket-database](https://github.com/flibustier/pokemon-tcg-pocket-database)** repository (maintained by [flibustier](https://github.com/flibustier/)). It maps the datamined image filenames to their integers, runs them through [the reverse-engineered binary layout](../scripts/deck_code.py), and encodes the result in `base64`.

