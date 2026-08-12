# V1 data integration and quality audit

## Purpose

The V1 analysis table is accepted only after its candidate-to-final-row losses,
identifier integrity, missingness, duplicates, rating ranges, and ambiguous
records are quantified. Generate the local audit artifacts with:

```bash
python3 scripts/audit_real_v1.py
```

## Matching and loss accounting

The snapshot uses stable identifiers from MovieLens `links.csv`. All 999 TMDB
responses returned the same IMDb ID as the linked candidate. No title-only or
fuzzy matches were needed.

Starting from 1,000 candidates:

- one TMDB ID returned HTTP 404;
- 58 responses had fewer than the required 50 TMDB votes; and
- 941 movies remained in the complete analysis table, for 94.1% coverage.

The local rejection CSV records every excluded candidate and its reason.

## Quality checks

The final 941-row table has unique MovieLens, IMDb, and TMDB identifiers. Every
stored field is present, and the three rating columns remain within the unified
1–10 analysis scale. The eligible TMDB response IDs exactly equal the processed table
IDs.

Five stable-ID matches have release years differing by more than one year
between the candidate table and TMDB. They are retained as diagnostic
differences because the independently returned IMDb IDs agree exactly. They are
not uncertain title matches.

## Manual review

The audit always creates `v1_manual_review.csv`, including when it contains zero
rows. V1 has no ambiguous records requiring manual judgment. A future stable-ID
mismatch would be placed in that file and would fail validation.

## Frozen analysis dataset

`v1_dataset_freeze.json` records the analysis table row and column counts,
ordered column names, processed-data SHA-256, candidate-table SHA-256, TMDB
collection checksum, quality-report checksum, and the exact generation and
audit entrypoints. Any later data refresh must create a new freeze record and
regenerate downstream results rather than silently reusing V1 conclusions.

All generated audit artifacts remain local and excluded from Git. The audit
logic, tests, and this interpretation are tracked.
