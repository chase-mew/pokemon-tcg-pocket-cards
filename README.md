# 🎴 Pokémon TCG Pocket Cards

<p align="center">
  <img alt="npm version" src="https://img.shields.io/npm/v/pokemon-tcg-pocket-cards">
  <img alt="npm downloads" src="https://img.shields.io/npm/dm/pokemon-tcg-pocket-cards">
  <img alt="licence" src="https://img.shields.io/npm/l/pokemon-tcg-pocket-cards">
  <img alt="last commit" src="https://img.shields.io/github/last-commit/chase-mew/pokemon-tcg-pocket-cards">
  <img alt="repo size" src="https://img.shields.io/github/repo-size/chase-mew/pokemon-tcg-pocket-cards">
</p>

This open-source repository holds data on Pokémon TCG Pocket cards. You can use it to build websites, collection trackers, and fan tools.

You can pull the raw JSON directly as an API:

- Full dataset: **[data/v5/cards.json](https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/data/v5/cards.json)** ([minified](https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/data/v5/cards.min.json))
- Core payload: **[data/v5/cards.core.json](https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/data/v5/cards.core.json)** ([minified](https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/data/v5/cards.core.min.json))
- Expansions and packs: **[data/v5/expansions.json](https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/data/v5/expansions.json)** ([minified](https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/data/v5/expansions.min.json))

Or install it from npm, which ships the minified data plus TypeScript definitions:

```bash
npm install pokemon-tcg-pocket-cards
```

### 📥 npm entry points

| Import | Contents |
| --- | --- |
| `pokemon-tcg-pocket-cards` | Full v5 card dataset (latest) |
| `pokemon-tcg-pocket-cards/v5` | Full v5 card dataset (pinned to v5) |
| `pokemon-tcg-pocket-cards/v5/core` | Slim core payload: diamonds and promos only, 14 fields per card |
| `pokemon-tcg-pocket-cards/core` | Alias of `/v5/core` for existing consumers |
| `pokemon-tcg-pocket-cards/v5/expansions` | Expansions and packs (pinned to v5) |
| `pokemon-tcg-pocket-cards/expansions` | Expansions and packs (latest) |
| `pokemon-tcg-pocket-cards/v4` | Legacy v4 card dataset |
| `pokemon-tcg-pocket-cards/v4/expansions` | Legacy v4 expansions |
| `pokemon-tcg-pocket-cards/v1`, `/v2`, `/v3` | Legacy datasets, JSON only |

```js
import cards from "pokemon-tcg-pocket-cards";
import core from "pokemon-tcg-pocket-cards/v5/core";

// Full payload: every field, nested attacks and abilities.
console.log(cards[0].attacks);

// Core payload: gameplay rarities only, about 0.9 MB, suited to web clients.
console.log(core[0].deckBuilderNr);
```

The pinned imports (`/v5`, `/v5/core`, `/v5/expansions`) keep their resolution when a future major version replaces the root import, so existing consumers can upgrade on their own schedule

Open a pull request if you find missing cards or errors.

### 📦 Moved files

Every dataset now lives under [data/](data/). If you link to a raw file at the repository root, update the URL:

| Old (removed)          | New                                                                    |
|------------------------|------------------------------------------------------------------------|
| `/v1.json`             | [data/v1/cards.json](data/v1/cards.json) ([minified](data/v1/cards.min.json))   |
| `/v2.json`             | [data/v2/cards.json](data/v2/cards.json) ([minified](data/v2/cards.min.json))   |
| `/v3.json`             | [data/v3/cards.json](data/v3/cards.json) ([minified](data/v3/cards.min.json))   |
| `/v4.json`             | [data/v4/cards.json](data/v4/cards.json) ([minified](data/v4/cards.min.json))   |

## ⚡ Adding a new expansion

When a new expansion drops, run the script to scrape card data, download card art, and update the JSON files.

```bash
pip install -r requirements.txt
python3 scripts/add_expansion.py <SET_CODE>
```

You can also scrape a chronological range of sets by linking them with an arrow.
```bash
python3 scripts/add_expansion.py a1->b4
```

The script handles these tasks:
1. Detects the expansion name and release date.
2. Scrapes all cards in the specified set or range.
3. Maps internal game asset IDs to `deckBuilderNr`.
4. Downloads [pack and card images](images/).
5. Appends new card records to the target **[JSON](data/v5/cards.json)** database.
6. Adds the expansion entry to the **[expansions](data/v5/expansions.json)** index.

### 🔄 Updating promo sets

Promo sets like P-A and P-B gain cards over time. Run the same command to pull new cards without duplicating existing ones:

```bash
python3 scripts/add_expansion.py PB
```

### ⚙️ Options

- Pass `--name "Custom Name"` to override the expansion name.
- Pass `--skip-images` to skip downloading images.
- Pass `--mode v4` to format the output for the legacy schema.

## 📊 Schema comparison

| **Feature**                        | **[💛 V4](data/v4/cards.min.json)** | **[🟦 V5 (core)](data/v5/cards.core.json)**                        | **[💚 V5 (full)](data/v5/cards.json)** (latest)                                 |
|------------------------------------|---------------------------|--------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| Missing values                     | Empty strings ("")        | null                             | null                                                         |
| Image formats                      | PNG only                  | WEBP only                        | WEBP (default) and PNG                                       |
| Data structure                     | Flat                      | Flat, 14 fields per card         | Mostly flat, with nested `ability` and `attacks` fields      |
| Booleans                           | Strings (`"Yes"`/`"No"`)   | Native booleans (`true`/`false`) | Native booleans (`true`/`false`)                             |
| Set mapping                        | Pack name                 | Set code and pack name           | Set name, ID and pack name                                   |
| Combat stats                       | Health only               | Health and points                | Health, retreat cost, weakness                               |
| Attack data                        | ❌                         | ❌                                | ✅ Structured (cost, name, damage, effect)                    |
| Abilities                          | ❌                         | ❌                                | ✅ Structured (exists, name, effect)                          |
| Game metadata                      | Rarity string, ex, artist | Type/subtype, stage, rarity, ex, mega | Type/subtype, stage, evolves_from, rarity, pack_points, ex, points, artstyle, artist |
| Shiny or Mega                      | ❌                         | ✅ Mega (`true`/`false`); shiny dropped | ✅ Native booleans (`true`/`false`)                           |
| Special tags                       | ❌                         | ❌                                | Ancient, future, and ultra beasts                            |
| Deck builder                       | ❌                         | ✅ Internal asset ID (`deckBuilderNr`) | ✅ Internal asset ID (`deckBuilderNr`)                        |
| Alternate prints                   | ⚠️ Exists, but as individual cards | ❌                                | ✅ Array of alternative set and rarity versions on each card  |
| Release date                       | ❌                         | ❌                                | ✅ ISO release date                                           |
| Flavour text                       | ❌                         | ❌                                | ✅ Raw text string                                            |
| Language support                   | English only              | English only                     | English only                                                 |
| Pack drop probabilities            | ❌                         | ❌                                | ❌                                                            |
| Payload size (minified)            | ~1 MB                     | ~0.9 MB                          | ~4.4 MB                                                      |

### 💼 Support schedule

[💚 V5](data/v5/cards.json) is the actively maintained data model.
[💛 V4](data/v4/cards.min.json) receives updates until the end of the "B" block (its final expansion).
Versions [V3](data/v3/cards.json) and earlier are fully deprecated and no longer updated.

## 🤝 Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for how to add
card data and the licensing split, the [Code of Conduct](CODE_OF_CONDUCT.md)
before opening a pull request, and [SECURITY.md](SECURITY.md) if you have found a
vulnerability rather than a bug.

## 🛠️ Projects using this API

- **[Pocket Decks Top](https://pocketdecks.top/)** A site that ranks top tournament decks every Monday.
- [Pocket Card Collection](https://github.com/rhuangabrielsantos/pokemon-tcg-pocket-cards) A progress tracker that saves collection data across devices with Google Sign in.
- [PTCGP Pack Opener](https://github.com/rohannishant/ptcgp-pack-opener) A pack opening simulator.
- [All Your Poke Cards](https://github.com/manelbrioude/allyourpokecards) A card information viewer.
- [Pokemon Pocket Card Data](https://github.com/nathanrboyer/PokemonPocketCardData) A notebook that helps you pick packs based on target pulls.
- [Pokemon TCG Pocket Trade Dex](https://github.com/bitmaybewise/pokemon-tcg-pocket-tradedex) A tool to compare card collections between players.

Submit a pull request to list your project here if you build something with this data!

## 💾 Data Source

Card data is scraped from **[Limitless TCG](https://pocket.limitlesstcg.com/cards).**
Deck builder numbers are derived using game asset mappings from the community **[pokemon-tcg-pocket-database](https://github.com/flibustier/pokemon-tcg-pocket-database)**, provided under the MIT License, Copyright (c) 2025 **[Jon (flibustier)](https://github.com/flibustier)**.

## 📜 Licence

- **💚 Version 5** (**[cards.json](data/v5/cards.json)**), **[expansions.json](data/v5/expansions.json)**, and code additions created for **version 5 or later** are licensed under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.en.html#license-text) (`AGPL-3.0-or-later`).
See **[LICENSE](LICENSE)** for the full license text.
- Legacy card datasets (**[v1.json](data/v1/cards.json), [v2.json](data/v2/cards.json), [v3.json](data/v3/cards.json), [v4.json](data/v4/cards.min.json)**) remain available under the original [MIT License](https://spdx.org/licenses/MIT.html).
See **[LICENSE-MIT](LICENSE-MIT)** for details.
- Third-party components and their notices: **[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)**.
