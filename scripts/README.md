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

## `collect_tmdb.py`

Collects one or more TMDB discover pages into a timestamped local snapshot.
Authentication comes from the `TMDB_BEARER_TOKEN` environment variable; the
token is sent in the request header and is never written to the cache.

```bash
export TMDB_BEARER_TOKEN="your_api_read_access_token"
python3 scripts/collect_tmdb.py --pages 1
```

Responses are cached for 24 hours by default. Add `--refresh` when a fresh
snapshot must come directly from the API.

## `generate_demo_data.py`

Creates the small tracked dataset used when no downloads or API credentials are
available. The output is deterministic and contains fictional movies only.

```bash
python3 scripts/generate_demo_data.py
```
