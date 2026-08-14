# How-to guides

## Add a new expansion

When a new set is released on Limitless TCG, pass the set code to the expansion script.

```bash
python3 scripts/add_expansion.py b4a
```

## Update promo sets

Promo sets add cards over time. Running the command for a promo set fetches only the newly added cards. It ignores existing entries to prevent duplication.

```bash
python3 scripts/add_expansion.py pb
```

## Scrape a chronological range of sets

If you are building the database from scratch or need to backfill multiple sets, use the arrow syntax (`->`). The script resolves the timeline and scrapes every set in order.

```bash
python3 scripts/add_expansion.py a1->b4
```

## Output data for legacy schemas

If your application still relies on the flat V4 schema, you can force the scraper to output V4 formatted data. Add the `--mode v4` flag o format the output for the legacy schema.
```bash 
python3 scripts/add_expansion.py b4 --mode v4
```