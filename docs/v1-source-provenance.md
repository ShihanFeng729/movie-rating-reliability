# V1 source provenance

The V1 snapshot combines three sources with different reference times. The
local machine-readable manifest is generated with:

```bash
python3 scripts/build_v1_source_manifest.py
```

It records the source URL, dataset/version description, reference time, file
size, SHA-256 checksum, and the official MovieLens 32M MD5 where available.
For TMDB it records the API endpoint pattern, collection-time range, response
count, aggregate byte size, and a deterministic collection checksum. It never
records the API credential or machine-specific absolute paths.

## Static source files

| Source | Dataset or version | Reference time | Files |
|---|---|---|---|
| IMDb | Non-commercial datasets, refreshed daily | Recorded at download | `title.basics.tsv.gz`, `title.ratings.tsv.gz` |
| MovieLens | MovieLens 32M | Generated 2023-10-13 | `ml-32m.zip` |

IMDb files were downloaded from `https://datasets.imdbws.com/`. MovieLens 32M
was downloaded from `https://files.grouplens.org/datasets/movielens/` and its
official MD5 was verified in addition to the locally recorded SHA-256.

## API source

TMDB movie details use API v3 and the stable endpoint
`/movie/{tmdb_id}?language=en-US`. Each successful response preserves its own
UTC retrieval time. The V1 run saved 999 responses; one candidate ID returned
HTTP 404. The credential remains only in the ignored local `.env` file.

## Reproducibility boundary

The generated manifest stays local because it describes locally held source
artifacts. This documentation and the generator are tracked, while source
files, API responses, processed data, and generated reports remain excluded
from Git according to their source terms and the repository data policy.

Because MovieLens is fixed in 2023 while IMDb and TMDB were observed later,
rating drift is an explicit limitation. The manifest supports reconstruction
and audit; it does not make the three sources simultaneous.
