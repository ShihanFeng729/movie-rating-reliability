# Scripts

This directory will contain small command-line helpers for tasks such as:

- downloading approved data sources
- refreshing cached API data
- preparing demo data
- running repeatable maintenance steps

Reusable project logic should remain in `src/`.

## `download_data.py`

Downloads the public IMDb title/rating files and either the small development
or stable research version of MovieLens. It saves data under `data/external/`
and writes a checksum manifest, while Git ignores the downloaded files.

```bash
python3 scripts/download_data.py --help
```
