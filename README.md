# 🎴 Pokémon TCG Pocket Cards

This open-source repository holds data on Pokémon TCG Pocket cards. You can use it to build websites, collection trackers, and fan tools.

You can pull the raw JSON directly as an API:

- Cards dataset: **[https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/v5.json](https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/v5.json)**
- Expansions and packs: **[https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/expansions.json](https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/expansions.json)**

Open a pull request if you find missing cards or errors.

## 💾 Data Source

Card data is scraped from **[Limitless TCG](https://pocket.limitlesstcg.com/cards).**

## ⚡ Adding a new expansion

When a new expansion drops, run a single script to scrape card data, download card art, and update the JSON files:

```bash
pip install -r requirements.txt
python3 scripts/add_expansion.py <SET_CODE>
```

For example:
```bash
python3 scripts/add_expansion.py b4a
```

The script handles five tasks:
1. It detects the expansion name from Limitless TCG.
2. It scrapes all cards in the set.
3. It downloads pack and card images.
4. It appends new card records to **[v5.json](v5.json)**.
5. It adds the expansion entry to **[expansions.json](expansions.json)**.

### 🔄 Updating promo sets

Promo sets like P-A and P-B gain cards over time. Run the same command to pull new cards without duplicating existing ones:

```bash
python3 scripts/add_expansion.py PA
python3 scripts/add_expansion.py PB
```

### ⚙️ Options

- Pass `--name "Custom Name"` to override the expansion name.
- Pass `--skip-images` to skip downloading images.

## 📊 Schema comparison

| **Feature**   | **[💛 V4](v4.json)** | **[💚 V5](v5.json)** (newer)                            |
|----------------|----------------------|---------------------------------------------------------|
| Missing values | Empty strings ("")   | null                                                    |
| Image formats  | PNG only             | WEBP (default) and PNG                                  |
| Data structure | Flat                 | Mostly flat, with nested `ability` and `attacks` fields |
| Booleans       | Strings ("Yes"/"No") | Native booleans (true/false)                            |
| Set mapping    | Pack name            | Set ID and pack name                                    |
| Combat stats   | Health only          | Health, retreat cost, weakness                          |
| Attack data    | None                 | Structured (cost, name, damage, effect)                 |
| Abilities      | None                 | Structured (exists, name, effect)                       |
| Game metadata  | Rarity string        | Pack points, stage, evolves_from, shiny, points         |
| Release date   | None                 | ISO release date                                        |
| Card text      | None                 | Raw text for Trainers                                   |

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

- **💚 Version 5** (**[v5.json](v5.json)**), **[expansions.json](expansions.json)**, and code additions created for **version 5 or later** are licensed under the **[GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.en.html#license-text)** (`AGPL-3.0-or-later`).    
See **[LICENSE](LICENSE)** for the full license text.
- Legacy card datasets (**[v1.json](v1.json), [v2.json](v2.json), [v3.json](v3.json), [v4.json](v4.json)**) remain available under the original **[MIT License](https://spdx.org/licenses/MIT.html)**.     
See **[LICENSE-MIT](LICENSE-MIT)** for details.
- Pokémon card images, names, text, and logos remain the intellectual property of Nintendo, Creatures Inc., GAME FREAK Inc., and DeNA. This project is an independent fan work.