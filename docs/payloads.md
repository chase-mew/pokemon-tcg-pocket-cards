# Choosing a data file

The package ships the same 3,879-card dataset in several shapes. All cover the
same cards unless noted; the difference is which fields each record carries and
how much bandwidth the download costs. Every file exists as a readable
`.json` and a compact `.min.json`.

## Which file do I need?

| You are building... | Use | Import | Minified size |
| --- | --- | --- | --- |
| A web app that shows cards and needs images | **core** | `pokemon-tcg-pocket-cards/v5/core` | ~0.96 MB |
| The same, with images served from your own CDN | **core no-image** | `pokemon-tcg-pocket-cards/v5/core/no-image` | ~0.59 MB |
| A battle simulator, damage calculator or deck tool | **gameplay** | `pokemon-tcg-pocket-cards/v5/gameplay` | ~1.24 MB |
| A collection tracker, set browser or wiki | **collection** | `pokemon-tcg-pocket-cards/v5/collection` | *(planned, see below)* |
| Anything that must not break while you catch up | **full** | `pokemon-tcg-pocket-cards` | ~4.58 MB |
| Can't be bothered to update right now (or ever) | **v4** | `pokemon-tcg-pocket-cards/v4` | ~1.05 MB |

Raw JSON (no npm) works too: swap the import for the matching file under
`data/v5/` on GitHub or a CDN, for example
`https://raw.githubusercontent.com/chase-mew/pokemon-tcg-pocket-cards/refs/heads/main/data/v5/cards.core.min.json`.

## What each payload contains

### gameplay: the combat model (18 fields, deeper records)

Everything a simulator needs: identity (`id`, `name`, `deckBuilderNr`), rules
(`type`, `subtype`, `stage`, `evolves_from`, `special_tags`, `ex`, `mega`),
and combat (`health`, `retreat`, `weakness`, `ability`, `attacks`,
`card_text`, `points`). `ability` and `attacks` are nested objects, which is
why this file is larger than core despite omitting `rarity`, `pack` and
images. Rarity still filters the card range (see below). Schema:
[cards.gameplay.schema.json](../data/v5/cards.gameplay.schema.json) ·
[types](../data/v5/cards.gameplay.d.ts)

### core: the flat summary (14 fields)

One flat record per card: `id`, `name`, `set_code`, `pack`, `type`, `subtype`,
`stage`, `rarity`, `ex`, `mega`, `health`, `points`, `deckBuilderNr`, `image`.
No nested objects, images included, collection metadata absent. The right
default when you want most of the dataset at a fraction of the full size.
Schema: [cards.core.schema.json](../data/v5/cards.core.schema.json) ·
[types](../data/v5/cards.core.d.ts)

### core no-image: core minus `image` (13 fields)

Identical to core with the image URL dropped. Use it when you derive image
paths yourself (per-set image shards, your own storage) and want the smallest
download that still describes every card. Schema:
[cards.core.no-image.schema.json](../data/v5/cards.core.no-image.schema.json) ·
[types](../data/v5/cards.core.no-image.d.ts)

### collection: the tracker's view (all prints, collection fields)

One record per **printed card** (all 3,879, including star rares and Crown
Rare, which the other projections exclude): `id`, `name`, `set_code`,
`set_name`, `pack`, `release_date`, `rarity`, `pack_points`, `art_style`,
`artist`, `flavour_text`, `alternate_versions`, `image`, `image_png`, the
collectable traits `ex`, `mega`, `shiny`, `special_tags`, plus the trading
fields `tradable`, `sharable` and `trade_cost`. It carries no gameplay data:
pair it with gameplay or core when a tool needs both. Schema:
[cards.collection.schema.json](../data/v5/cards.collection.schema.json) ·
[types](../data/v5/cards.collection.d.ts)

A `collection/no-image` sister drops `image` and `image_png` (14 remaining
fields) for trackers that derive image paths themselves.

Trading fields (derived from rarity):

| Rarity | `tradable` | `sharable` | `trade_cost` |
| --- | :-: | :-: | --- |
| ◊, ◊◊ | true | true | 0 |
| ◊◊◊ | true | true | 1200 |
| ◊◊◊◊ | true | true | 5000 |
| ☆ illustration rare (not shiny) | true | false | 4000 |
| ☆ shiny | true | false | 10000 |
| ☆☆ full art (not shiny) | true | false | 25000 |
| ☆☆ shiny full art | true | false | 30000 |
| ☆☆☆, Crown Rare, Promo | false | false | null |

### full: everything the scraper extracts (30 fields)

The complete dataset: collection metadata (`set_name`, `pack`, `release_date`,
`pack_points`, `rarity`, `art_style`, `artist`, `flavour_text`,
`alternate_versions`), images in both formats, and every gameplay field.
Records keep all 30 keys with `null` for fields that do not apply. Licensed
AGPL-3.0-or-later like the rest of version 5. Schema:
[cards.schema.json](../data/v5/cards.schema.json) ·
[types](../data/v5/cards.d.ts)

## Rules the projections follow

**Card range.** core, core no-image and gameplay contain only gameplay
rarities: `◊`, `◊◊`, `◊◊◊`, `◊◊◊◊` and `Promo` (2,822 of 3,879 cards). Star
rares and Crown Rare are excluded because every one of them shares its
`deckBuilderNr` with a kept card: they are cosmetic variants, not different
game pieces. The full payload keeps all 3,879.

This filter has one consequence worth stating plainly: the projections are
not card-complete. Every `☆`, `☆☆`, `☆☆☆` and Crown Rare print is absent,
including 417 `ex` prints and all 37 Crown Rares, so a payload is the wrong
source for set-completion views, collectable checklists or any tool that must
show one row per printed card. A deck tool is unaffected: for every excluded
print, the deck-legal card with the same `deckBuilderNr` is present. Use the
full payload when print-level completeness matters.

**Sparse records.** Projection records omit any field whose value is null.
Trainer records also omit `ex` and `mega`, and in gameplay they are trimmed
further: a non-Fossil Trainer keeps only `id`, `name`, `set_code`, `type`,
`subtype`, `card_text` and `deckBuilderNr` (Fossils are the exception below).
An absent key means the source value was null or the field was trimmed, and a
few absences carry meaning rather than absence of data: a Fossil omits
`retreat` because it cannot retreat, not because retreat does not apply. The
schema for each payload is the authoritative field list, linked from each
section below. The full payload keeps every key with nulls.

**Fossil exception.** Fossil trainers (Helix, Dome, Skull, Armor, Plume,
Cover, Jaw, Sail, Claw, Root) play as 40-HP Basic colourless Pokémon, so they
keep `stage`, `health`, `points` and `weakness` (`"none"`) in every
projection. They cannot retreat and have no attacks.

**Types.** Each projection ships a JSON Schema (validated in the test suite)
and a generated `.d.ts` behind a wrapper that also provides a default export.

## Entry points at a glance

| Import | Files |
| --- | --- |
| `pokemon-tcg-pocket-cards` | full (v5, follows the latest major) |
| `pokemon-tcg-pocket-cards/v5` | full, pinned to v5 |
| `pokemon-tcg-pocket-cards/v5/core` | core |
| `pokemon-tcg-pocket-cards/core` | alias of `/v5/core` |
| `pokemon-tcg-pocket-cards/v5/core/no-image` | core no-image |
| `pokemon-tcg-pocket-cards/core/no-image` | alias of `/v5/core/no-image` |
| `pokemon-tcg-pocket-cards/v5/gameplay` | gameplay |
| `pokemon-tcg-pocket-cards/gameplay` | alias of `/v5/gameplay` |
| `pokemon-tcg-pocket-cards/expansions` | expansions index (latest) |
| `pokemon-tcg-pocket-cards/v5/expansions` | expansions index, pinned |
| `pokemon-tcg-pocket-cards/v4`, `/v4/expansions` | legacy v4 cards and index |
| `pokemon-tcg-pocket-cards/v1`, `/v2`, `/v3` | legacy JSON, no types |

Pinned `./v5/...` entries keep their resolution when the root import moves to a
future major; the unpinned aliases exist for consumers already importing them.

## Field comparison across payloads

The full schema comparison lives in the
[README](../README.md#-schema-comparison). The short version:

| Field group | core | gameplay | full |
| --- | :-: | :-: | :-: |
| Identity (`id`, `name`, `deckBuilderNr`) | ✅ | ✅ | ✅ |
| Set context (`set_code`; full adds `set_name`, `pack`, `release_date`) | set_code only | set_code only | ✅ |
| Rules (`type`, `subtype`, `stage`, `evolves_from`, `ex`, `mega`, `special_tags`) | partial (no `evolves_from`, `special_tags`) | ✅ | ✅ |
| Combat (`health`, `points`, `retreat`, `weakness`) | partial (no `retreat`, `weakness`) | ✅ | ✅ |
| Attacks and abilities | ❌ | ✅ nested | ✅ nested |
| Rules text (`card_text`) | ❌ | ✅ | ✅ |
| Rarity and collection metadata | ❌ | ❌ | ✅ |
| Images | ✅ webp | ❌ | ✅ webp + png |
| Flavour text, artist, alternate prints | ❌ | ❌ | ✅ |

Every gameplay-rarity card appears in each payload exactly once; the columns
differ only in fields, never in card coverage (the full payload adds the
cosmetic rarities on top)
