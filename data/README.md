# Data directory

The repository tracks this directory structure but does not track raw,
licensed, cached, or generated datasets.

- `raw/`: immutable files downloaded from original sources
- `external/`: third-party datasets such as IMDb and MovieLens
- `interim/`: temporary outputs between processing steps
- `processed/`: analysis-ready datasets
- `cache/`: replaceable API responses and download caches

Future download commands and data-license notes will be documented here.
Synthetic test fixtures will live under `tests/`, not in these data folders.
