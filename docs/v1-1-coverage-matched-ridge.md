# V1.1 coverage-matched Ridge baseline

The third V1.1 step establishes the fair no-sentiment comparison for the
strict review-coverage sample. It does not train Ridge on the 149 newer movies.

## Fixed comparison design

The original V1 temporal split remains unchanged:

- the same 752 older movies define training data;
- the same inner temporal validation selects Ridge alpha from `0.1`, `1.0`,
  and `10.0`;
- the original outer test contains 189 movies released from 2015–2022; and
- final metrics are recalculated only on the 149 outer-test movies that have
  strict, pre-2023-10-13 English review features.

The coverage table is joined back to the ratings table using matching
MovieLens, IMDb, and TMDB IDs. A mismatch or a coverage movie outside the fixed
outer holdout stops the run. The model uses no sentiment value in this step.

This design isolates sample composition. The sentiment experiment used the
identical 752 training rows, 149 evaluation movies, temporal partitions,
preprocessing, alpha candidates, and metrics; its only intended difference was
the predefined sentiment feature.

## Run locally

After building the strict sample and sentiment feature table, run:

```bash
python3 scripts/analyze_v1_1_coverage_matched_ridge.py
```

The ignored output
`reports/generated/v1_1_coverage_matched_ridge.json` records the selected
alpha, MAE, RMSE, R², reference baselines, coefficients, grouped errors, and
movie-level diagnostics. No real generated report is committed.

## Frozen result

The complete run retains all 752 original training movies and evaluates 149 of
the 189 fixed outer-test movies, spanning 2015–2022. Inner temporal validation
again selects `alpha = 10.0`. The no-sentiment Ridge obtains MAE `0.2040`, RMSE
`0.2908`, and R² `0.8997`. On the identical 149 movies, the TMDB–MovieLens
average baseline has MAE `0.2273` and the training-mean baseline has MAE
`0.7320`.

The sentiment-augmented Ridge was compared against the `0.2040` MAE on these
exact movies. It did not reach the required MAE of no more than `0.1940` or the
separate time-subgroup criterion. This rating-only model is therefore preferred
for the completed V1.1 experiment; see
[`v1-1-closure.md`](v1-1-closure.md).

The sorted 149-movie ID set has SHA-256
`5d2edc4fbf95f7a7092be613cca17b4234b2d9c57557e200701763dcd397468f`.
The generated local report has SHA-256
`a37b80ae0500d6866da113334325904eb037b7c1a3affa7ecc3d34d19ef68243`.
