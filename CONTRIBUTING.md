# Contributing

Thanks for wanting to improve the dataset.

## Ground rules

Read the [Code of Conduct](CODE_OF_CONDUCT.md) first. It applies to every
interaction here.

Report a security issue through [SECURITY.md](SECURITY.md) rather than a public
issue.

## Adding or fixing card data

Card data comes from the scraper. To add a new expansion:

```bash
pip install -r requirements.txt
python scripts/add_expansion.py <SET_CODE>
```

Use `--mode v4` for the legacy v4 schema. Link sets with an arrow to scrape a
range, for example `a1->b4`.

A pull request that runs the script is preferred over hand-editing the JSON,
because the script keeps the schema and the image assets consistent with the
data.

## Licensing

Contributions to the version 5 datasets and to code written for version 5 or
later fall under AGPL-3.0-or-later. The legacy v1 to v4 datasets stay under the
original MIT licence. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for
the full split.

## Pull requests

Keep changes focused. Describe what changed and why in the pull request body.
The maintainer reviews every pull request.
