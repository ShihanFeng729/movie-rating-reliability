# V1.1 closure record

## Final status

**V1.1 is complete as a documented No-Go sentiment experiment.** The fixed
sentiment extension reduced MAE by `0.0011`, below the predefined `0.0100`
minimum, and improved only two of four predefined time groups rather than the
required three. The coverage-matched rating-only Ridge is therefore the
preferred model for this experiment.

The sentiment implementation, tests, and decision report builder remain in the
repository so the negative result can be reproduced. No additional sentiment
models will be fitted or tuned against the existing outer holdout.

## Deliberately omitted sensitivity analysis

The earlier plan allowed an optional sensitivity analysis using reviews created
after the strict MovieLens boundary but before the later IMDb snapshot. It is
not run because it cannot change the predeclared primary decision and would use
a weaker timing boundary. Omitting it protects the interpretation of the fixed
experiment; it is not missing implementation work.

## Data-retention and regression checks

- Raw TMDB review responses remain under ignored local data paths.
- Processed text, author data, numeric sentiment features, and enriched rating
  tables remain under ignored `data/processed/` paths.
- Generated comparison and decision reports remain under ignored
  `reports/generated/` paths.
- No API token or local environment file is tracked.
- An automated repository-policy test checks representative sensitive paths
  with Git on every test run.
- The credential-free demo and the full automated test suite remain the public
  regression checks.

Useful verification commands are:

```bash
git check-ignore data/raw/tmdb/v1_reviews/example.json
git check-ignore data/processed/v1_1_sentiment_features.csv
git check-ignore reports/generated/v1_1_sentiment_decision.json
python3 run.py
python3 -m pytest
```

## Next research stage

V1.2 will audit when the unchanged rating-only Ridge is less reliable. It is a
descriptive residual analysis, not another model-selection round. Its frozen
scope is documented in [`v1-2-error-audit-plan.md`](v1-2-error-audit-plan.md).
