# V1.2 prediction-error reliability audit plan

## Purpose

V1.2 asks: **under which observable conditions is the unchanged rating-only
Ridge more likely to make a larger IMDb-rating prediction error?** The goal is
to explain reliability boundaries before presentation work begins, not to tune
the model or claim that any condition causes an error.

The audit uses the existing 752/189 temporal split and the already frozen Ridge
predictions. It does not refit the model, change `alpha`, add features, remove
movies, or select a better model after inspecting the outer holdout.

## Predeclared questions

1. **Cross-platform disagreement:** does absolute Ridge error increase as the
   absolute TMDB–MovieLens rating difference increases?
2. **Rating support:** are errors larger for movies with fewer MovieLens or
   TMDB ratings?
3. **Release period:** is error size or direction different across the four
   already fixed two-year groups from 2015 through 2022?
4. **Primary genre:** which eligible genre groups have higher or lower error,
   with every group meeting the minimum size reported rather than selected?
5. **Target extremity:** are very high or low IMDb outcomes harder to predict
   than outcomes near the training-period center?
6. **Model-specific versus inherent difficulty:** do the same conditions also
   challenge the TMDB–MovieLens average baseline, or mainly the Ridge?

## Frozen analysis rules

- Evaluate all 189 outer-test movies; do not create a more favorable subset.
- Verify the outer-test MovieLens IDs and prediction values match the frozen V1
  evaluation before calculating diagnostics.
- Define any data-dependent cut points from the 752 training movies only.
- Reuse existing MovieLens support bands and the four fixed time groups.
- Report primary-genre groups only when they contain at least five holdout
  movies, and report every eligible group.
- For each group, report movie count, MAE, mean signed residual
  (`prediction − actual`), and a deterministic paired-bootstrap 95% interval
  for MAE using seed `510`.
- Report Spearman associations for continuous disagreement and support
  variables alongside grouped summaries.
- Compare Ridge with the already frozen platform-average baseline on identical
  movies.
- Treat all findings as descriptive associations, not causal effects.

## Execution order

1. Freeze a machine-readable audit contract and verify the 189-movie identity.
2. Implement reusable residual-diagnostic functions with synthetic tests.
3. Rebuild the unchanged Ridge and reference-baseline predictions locally.
4. Generate the full declared audit without suppressing inconvenient results.
5. Review sample sizes, intervals, direction, and consistency across conditions.
6. Publish aggregate findings and at most two reproducible figures; keep all
   row-level real data and generated reports ignored.
7. Close V1.2 before beginning V2 presentation and interaction work.

## Acceptance criteria

- The same 189 movies and existing predictions are verified before analysis.
- No training, preprocessing, feature, parameter, or holdout decision changes.
- Every predeclared condition is reported with counts and uncertainty.
- Ridge and the platform-average baseline use identical rows.
- Tests cover grouping boundaries, residual direction, bootstrap determinism,
  identity rejection, and small-group suppression.
- Raw and processed real data remain untracked; only aggregate documentation
  and approved figures may be committed.
- The full test suite, credential-free demo, and Python 3.11–3.14 CI pass.

## Interpretation and future-model boundary

After this audit, the existing outer holdout becomes a diagnostic dataset and
must not be reused to claim unbiased performance for a newly tuned model. Any
future model change requires a separately specified version and a new temporal
test snapshot. V1.2 itself ends with explanation, not optimization.
