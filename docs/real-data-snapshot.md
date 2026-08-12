# V1 real-data snapshot contract

## Decision

The first real-data run starts with 1,000 candidate movies, targets 750 movies
with complete TMDB, IMDb, and MovieLens fields, and stops if fewer than 500
complete movies remain. The machine-readable definition is
[`config/real_snapshot_v1.json`](../config/real_snapshot_v1.json).

This three-level rule accounts for losses during identifier validation and
field filtering. A minimum of 500 complete movies also preserves at least 100
movies for the planned 20% holdout. The target of 750 leaves more room for
descriptive checks by release era, genre, and rating-count band without making
the initial API collection unnecessarily large.

## Sampling frame

MovieLens 32M is the sampling frame because its `links.csv` maps each
MovieLens movie to IMDb and TMDB identifiers. Starting from these stable IDs is
safer than sampling a TMDB popularity list and attempting title-only matching.

Eligible records must:

- be non-adult feature films released from 1980 through 2022;
- have MovieLens, IMDb, and TMDB identifiers;
- have at least 50 MovieLens ratings, 500 IMDb votes, and 50 TMDB votes; and
- pass the existing conservative identifier and title/year checks.

The upper release year is 2022 because MovieLens 32M was generated in October
2023. This gives included films some opportunity to accumulate MovieLens
ratings before that dataset's cutoff.

The sample is deterministic with seed `510`. It is stratified by release decade
and MovieLens rating-count band. Genre remains an analysis dimension rather
than a strict sampling quota because movies can have multiple genres and sparse
genre-by-decade combinations could otherwise make the rule unstable.

## Source-time limitation

The three sources are not simultaneous snapshots. MovieLens 32M is fixed in
2023, while the IMDb files are refreshed daily and TMDB values are captured at
collection time. Every output must preserve each source's own reference time.
Rating drift between those times is a study limitation and must not be described
as if all platforms were observed at the same instant.

## Evaluation boundary

The newest release years form a 20% holdout, with at least 100 test movies. The
split is fixed before Ridge preprocessing or regularization choices are learned.
This produces a more demanding check on newer, unseen movies than evaluating
only on the same sample used to develop the model.

Validate the contract without downloading data:

```bash
python3 scripts/validate_snapshot_contract.py
```

After downloading the real source files, build the pre-TMDB candidate table:

```bash
python3 scripts/build_real_candidates.py
```

This streams the 32 million MovieLens ratings instead of loading them all into
memory, joins IMDb fields by stable ID, applies the contract, and writes 1,000
rows to `data/interim/v1_candidates.csv`. A local audit summary is written to
`reports/generated/v1_candidate_summary.json`. Both outputs remain excluded
from Git.

Collect TMDB movie details for the linked IDs with:

```bash
python3 scripts/collect_candidate_tmdb.py
```

The command requests `/movie/{tmdb_id}` directly, saves one local record per
movie, and can resume after an interruption. It applies the 50-vote TMDB
threshold and writes the joined complete rows to
`data/processed/v1_movie_ratings.csv`. Its audit summary reports whether the
750-movie target or 500-movie minimum was reached. Raw, processed, and audit
outputs remain excluded from Git.

For a small connection and credential check, use `--limit 3`. A later full run
reuses those successful records and continues with the remaining candidates.

The collection command automatically reads a local `.env` file. Copy
`.env.example` to `.env`, replace the placeholder with the TMDB API Read Access
Token, and never commit that file. After the complete dataset reaches the
minimum, generate the V1 reliability and newest-movie holdout reports with:

```bash
python3 scripts/analyze_real_v1.py
```

Build the unified local provenance manifest with:

```bash
python3 scripts/build_v1_source_manifest.py
```

The tracked provenance documentation is in
[`v1-source-provenance.md`](v1-source-provenance.md).
