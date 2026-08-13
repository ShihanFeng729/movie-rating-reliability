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

## `collect_candidate_tmdb.py`

Fetches TMDB movie details by the stable IDs in the fixed V1 candidate table.
Each successful response is saved separately so an interrupted run can resume.

```bash
python3 scripts/collect_candidate_tmdb.py
```

The command reads `TMDB_BEARER_TOKEN` from the shell or the ignored local
`.env` file. Run `analyze_real_v1.py` after the complete dataset is collected
to generate real pairwise reliability, grouped and sensitivity analyses, and
the temporal Ridge holdout report.

Run `build_v1_source_manifest.py` after collection to create the local source
URL, version, reference-time, size, and checksum audit manifest.

Run `audit_real_v1.py` after the source manifest to quantify coverage,
rejections, missingness, duplicates, ambiguous records, and to freeze the
analysis-ready dataset metadata and checksums.

Run `generate_v1_figures.py` after `analyze_real_v1.py` to rebuild the two
published aggregate SVG result figures from the ignored local JSON summaries.

Responses are cached for 24 hours by default. Add `--refresh` when a fresh
snapshot must come directly from the API.

## `generate_demo_data.py`

Creates the small tracked dataset used when no downloads or API credentials are
available. The output is deterministic and contains fictional movies only.

```bash
python3 scripts/generate_demo_data.py
```
