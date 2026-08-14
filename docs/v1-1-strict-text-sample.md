# V1.1 strict text-sample freeze

V1.1 begins by freezing a reproducible review-text sample before any sentiment
score is calculated. This keeps sample selection separate from later modeling
choices.

## Inclusion rules

A review is included only when all of the following are true:

1. its movie belongs to the fixed 189-movie V1 temporal holdout;
2. its response is joined to that holdout by the stable TMDB movie ID;
3. its body is non-empty;
4. its creation timestamp is present and no later than
   `2023-10-13T00:00:00+00:00`, the frozen MovieLens 32M boundary; and
5. seeded `langdetect==1.0.9` classifies that individual review as English.

The builder aggregates accepted reviews into one row per movie, in a stable
order. It records review, word, and character counts as well as the earliest
and latest accepted timestamps. Author names, usernames, review identifiers,
profile details, and links are excluded.

## Local artifacts

Run:

```bash
python3 scripts/build_v1_1_strict_review_sample.py
```

The command creates two ignored local files:

- `data/processed/v1_1_strict_review_sample.jsonl` contains the text-bearing
  movie rows used by the next V1.1 steps.
- `reports/generated/v1_1_strict_review_sample.json` contains only aggregate
  filter losses, coverage, schema, and SHA-256 freeze hashes.

The JSONL hash is deterministic: repeated builds from identical inputs and
dependency versions produce the same sample hash. Generation time is stored
only in the separate summary and therefore does not affect that hash.

## Frozen result

The first complete build started with 507 non-empty reviews across the 189
holdout movies. The strict time rule removed 63 reviews, leaving 444. The
per-review language rule then removed three reviews (two classified as
Indonesian and one as Romanian), leaving 441 English reviews across 149
movies. Coverage therefore remains 78.84% of the fixed holdout.

The frozen JSONL SHA-256 is
`5e5943b0de4dd501dc42fa5c3f75236b907eb7d4798651ad888b06197cebf8e3`.
This identifies the exact local input for the next V1.1 step without exposing
its text.

## Scope and interpretation

The source audit collected only the first TMDB review page for each movie, so
this is a controlled feature-availability sample rather than a complete review
corpus. Movies without qualifying text remain outside the coverage-matched
V1.1 comparison. No sentiment label, score, or fitted model is created during
this freeze step.
