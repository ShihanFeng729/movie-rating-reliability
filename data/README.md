# Data directory

The repository tracks this directory structure but does not track raw,
licensed, cached, or generated datasets.

- `raw/`: immutable files downloaded from original sources
- `external/`: third-party datasets such as IMDb and MovieLens
- `interim/`: temporary outputs between processing steps
- `processed/`: analysis-ready datasets
- `cache/`: replaceable API responses and download caches

Synthetic test fixtures live under `tests/`, not in these data folders.

## Download commands

The development-sized source files can be downloaded with:

```bash
python3 scripts/download_data.py
```

This obtains two IMDb files and the small MovieLens dataset. For the stable
MovieLens 32M research dataset, run:

```bash
python3 scripts/download_data.py --movielens research
```

The command writes `external/download_manifest.json`, which records each
source URL, local path, file size, SHA-256 checksum, and retrieval time.
Existing files are skipped unless `--overwrite` is provided.

## TMDB snapshots

TMDB API responses are cached under `cache/tmdb/`. Each collection run creates
a separate UTC-timestamped folder under `raw/tmdb/` containing:

- `movies.jsonl`: one movie record per line
- `metadata.json`: collection settings, page counts, source URLs, cache/API
  status, and collection times

Both locations are ignored by Git because they contain reproducible local data.
See `scripts/README.md` for the collection command.
