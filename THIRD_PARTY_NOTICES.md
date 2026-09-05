# Third-party notices

This repository ships code and data from several sources under different
licences. This file records what came from where.

## Licence split

The repository as a whole is dual licensed, and which licence applies depends on
which file you are looking at.

| Part | Licence |
| --- | --- |
| Version 5 datasets, `data/v5/` | AGPL-3.0-or-later |
| code additions written for version 5 or later | AGPL-3.0-or-later |
| Legacy datasets `data/v1/` through `data/v4/` | MIT |
| Original code by Chase Manning, written before v5 | MIT |

`LICENSE` carries the AGPL text. `LICENSE-MIT` carries the MIT text. Source files
state which applies to them in their header.

## Pokémon TCG Pocket

Pokémon, Pokémon TCG Pocket and all related names and artwork are trademarks and
copyrights of Nintendo, Creatures Inc., GAME FREAK Inc. and DeNA. This project is
unofficial and not affiliated with them. Card and pack artwork is reproduced here
for reference alongside the card data.

## Deck share encoding

`scripts/deck_code.py` implements the deck share code format. The reverse
engineered encoding logic originates from Nirostar, provided under the MIT
License, Copyright (c) 2026 by Nirostar.

https://github.com/Nirostar

That logic was ported to Python in this repository as an AGPL-3.0-or-later
addition, Copyright (C) 2026 Leonid Dalin and Chase Manning.

## Deck builder numbering

Deck builder numbers derive from game asset mappings maintained by the community
project pokemon-tcg-pocket-database. Provided under the MIT License, Copyright
(c) 2025 by Jon (flibustier).

https://github.com/flibustier/pokemon-tcg-pocket-database

## Original project

This repository began as the work of Chase Manning. Everything written before
version 5 remains under the MIT License, Copyright (c) 2024 Chase Manning.

https://github.com/chase-mew

## Card data source

Card data is scraped from Limitless TCG at
https://pocket.limitlesstcg.com/cards. The scraped facts are reproduced here as
data, not as licensed code.
