# V1.1 sentiment-augmented Ridge

The fourth V1.1 step adds the predefined sentiment score to the existing Ridge
workflow without allowing outer-test information to define training or
preprocessing.

## Why training reviews were required

The original review audit covered only the 189 outer-test movies. A sentiment
coefficient cannot be learned from test movies, so this step separately
collects first-page TMDB reviews for all 752 fixed training movies. The same
`2023-10-13` cutoff, seeded per-review English filter, and frozen lexicon rule
are then applied.

The training collection completed with zero request failures. Of 752 movies,
381 had non-empty first-page text. Strict time and language filtering retained
613 reviews across 325 movies. The remaining 427 training movies stay in the
training set: their sentiment score is fixed to `0`, accompanied by a separate
`sentiment_available = 0` indicator. Covered movies receive
`sentiment_available = 1`, including text with zero lexicon hits.

## Leakage controls

- The original 752/189 temporal split is created before sentiment fitting.
- The final outer test is the same 149-movie ID set frozen by the
  coverage-matched baseline.
- Sentiment score scaling, the missingness indicator scaling, genre encoding,
  all other numeric scaling, and Ridge alpha selection use training partitions
  only.
- Alpha is selected from the unchanged `0.1`, `1.0`, and `10.0` candidates by
  the same inner temporal validation.
- MovieLens, IMDb, and TMDB IDs must all match before feature joining.
- Raw text, numeric feature tables, enriched ratings, and generated reports
  remain local and ignored by Git.

## Run locally

```bash
python3 scripts/collect_v1_1_training_reviews.py
python3 scripts/build_v1_1_training_sentiment_features.py
python3 scripts/analyze_v1_1_sentiment_ridge.py
```

The collector is resumable and defaults to five bounded workers. Each movie is
stored independently, so interruption does not discard completed requests.

## Initial model output

Inner validation selects `alpha = 10.0`. On the fixed 149-movie outer test, the
sentiment-augmented Ridge has MAE `0.2029`, RMSE `0.2881`, and R² `0.9015`.
The standardized sentiment-score coefficient is `0.0226`; the availability
indicator coefficient is `-0.0006`.

These are implementation-stage observations, not the final V1.1 decision. The
next reporting step must compare the model with the frozen no-sentiment MAE of
`0.2040`, calculate the predefined time subgroups, and apply the already fixed
success criteria without changing this model.

The frozen training strict-text SHA-256 is
`8d8896495184e81842094c7576f77ba8d2867133934fa3b25c15ec86c52d8f32`;
the training sentiment-feature SHA-256 is
`b86d97d34ec6163ceab4c0cfc4caac3c593800463e29db6ba73136d88b560faa`.
The generated local model report SHA-256 is
`56841f104005b606d8c2d96bb6260fa38a549d663c5b890f4228e8aa8c58e5f5`.
