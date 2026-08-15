# 🎴 Pokémon TCG Pocket Cards

This open-source repository holds data on Pokémon TCG Pocket cards. You can use it to build websites, collection trackers, and fan tools.

You can pull the raw JSON directly as an API:

- Cards dataset: **[https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/v5.json](https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/v5.json)**
- Expansions and packs: **[https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/expansions.json](https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/expansions.json)**

Open a pull request if you find missing cards or errors.

## 💾 Data Source

Card data is scraped from **[Limitless TCG](https://pocket.limitlesstcg.com/cards).**    
Deck share codes are derived using game asset mappings from the community **[pokemon-tcg-pocket-database](https://github.com/flibustier/pokemon-tcg-pocket-database)**, provided under the MIT License, Copyright (c) 2025 **[Jon (flibustier)](https://github.com/flibustier)**.


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
3. Maps internal asset IDs to generate deck share codes.
4. Downloads [pack and card images](images/).
5. Appends new card records to the target **[JSON](v5.json)** database.
6. Adds the expansion entry to the **[expansions](expansions.json)** index.

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

| **Feature**                        | **[💛 V4](v4.json)**      | **[💚 V5](v5.json)** (newer)                                                         |
|------------------------------------|---------------------------|--------------------------------------------------------------------------------------|
| Missing values                     | Empty strings ("")        | null                                                                                 |
| Image formats                      | PNG only                  | WEBP (default) and PNG                                                               |
| Data structure                     | Flat                      | Mostly flat, with nested `ability` and `attacks` fields                              |
| Booleans                           | Strings (`"Yes"`/`"No"`)  | Native booleans (`true`/`false`)                                                     |
| Set mapping                        | Pack name                 | Set name, ID and pack name                                                           |
| Combat stats                       | Health only               | Health, retreat cost, weakness                                                       |
| Attack data                        | ❌                         | ✅ Structured (cost, name, damage, effect)                                            |
| Abilities                          | ❌                         | ✅ Structured (exists, name, effect)                                                  |
| Game metadata                      | Rarity string, ex, artist | Type/subtype, stage, evolves_from, rarity, pack_points, ex, points, artstyle, artist |
| Shiny or Mega               | ❌                         | ✅ Native booleans (`true`/`false`)                                                   |
| Special tags | ❌ | Ancient, future, and ultra beasts                                                    |
| Deck builder | ❌ | Internal asset ID and deck share code                                                | 
| Alternate prints | ⚠️ Exists, but as individual cards | ✅ Array of alternative set and rarity versions on each card                          |
| Release date                       | ❌                         | ✅ ISO release date                                                                   |
| Flavour text                       | ❌                         | ✅ Raw text string                                                                    |               
| Language support | English only | English only |
| Pack drop probabilities            | ❌                         | ❌                                                                                    | 

### 💼 Support schedule

**[💚 V5](v5.json) is the actively maintained data model.**   
[💛 V4](v4.json) receives updates until the final expansion of the current season (or the start of the "C" block).   
Versions [V3](v3.json) and earlier are fully deprecated and no longer updated.

## 🛠️ Projects using this API

- **[Pocket Decks Top](https://pocketdecks.top/)** A site that ranks top tournament decks every Monday.
- [Pocket Card Collection](https://github.com/rhuangabrielsantos/pokemon-tcg-pocket-cards) A progress tracker that saves collection data across devices with Google Sign in.
- [PTCGP Pack Opener](https://github.com/rohannishant/ptcgp-pack-opener) A pack opening simulator.
- [All Your Poke Cards](https://github.com/manelbrioude/allyourpokecards) A card information viewer.
- [Pokemon Pocket Card Data](https://github.com/nathanrboyer/PokemonPocketCardData) A notebook that helps you pick packs based on target pulls.
- [Pokemon TCG Pocket Trade Dex](https://github.com/bitmaybewise/pokemon-tcg-pocket-tradedex) A tool to compare card collections between players.

Submit a pull request to list your project here if you build something with this data!

## 📜 License

- **💚 Version 5** (**[v5.json](v5.json)**), **[expansions.json](expansions.json)**, and code additions created for **version 5 or later** are licensed under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.en.html#license-text) (`AGPL-3.0-or-later`).    
See **[LICENSE](LICENSE)** for the full license text.
- Legacy card datasets (**[v1.json](v1.json), [v2.json](v2.json), [v3.json](v3.json), [v4.json](v4.json)**) remain available under the original [MIT License](https://spdx.org/licenses/MIT.html).     
See **[LICENSE-MIT](LICENSE-MIT)** for details.
- **[Reverse-engineered deck share encoding logic](/scripts/deck_code.py)** provided under the MIT License, Copyright (c) 2026 by **[Nirostar](https://github.com/Nirostar)**.    
It was ported to Python under [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.en.html#license-text) (`AGPL-3.0-or-later`), Copyright (C) 2026 **Leonid Dalin <[infoLeonid@protonmail.com](mailto:infoLeonid@Protonmail.com)> & Chase Manning <[chase@manning.dev](mailto:chase@Manning.dev)>**.
- Pokémon card images, names, text, and logos remain the intellectual property of Nintendo, Creatures Inc., GAME FREAK Inc., and DeNA. This project is an independent fan work.