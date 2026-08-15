# V1.1 fixed sentiment baseline

The second V1.1 step converts the frozen English review sample into one simple,
auditable sentiment feature per movie. The method is fixed before it is tested
against IMDb ratings or Ridge residuals.

## Scoring rule

The baseline uses compact positive and negative English word lists stored in
`sentiment_baseline.py`. Each matched positive word contributes `+1` and each
matched negative word contributes `-1`. A sentiment word is flipped when an
odd number of fixed negators occurs in the preceding three-token window.

For each movie:

```text
sentiment_score = (positive_hits - negative_hits) / total_lexicon_hits
```

The result ranges from `-1` to `1`. Text with no lexicon hits receives `0` and
is separately counted so that missing lexical evidence cannot be mistaken for
demonstrated neutral sentiment. The feature table also records positive and
negative hits, token count, and lexicon coverage.

This rule is deliberately modest. It does not detect sarcasm, mixed targets,
plot description, domain-specific phrases, or context beyond local negation.
Its value is transparency and a clean test of whether a predefined signal adds
information—not state-of-the-art sentiment classification.

## Local artifacts

After rebuilding the strict sample, run:

```bash
python3 scripts/build_v1_1_sentiment_features.py
```

The command writes two ignored local files:

- `data/processed/v1_1_sentiment_features.csv` contains movie-level numeric
  features and stable IDs, but no review text or author information.
- `reports/generated/v1_1_sentiment_baseline.json` records aggregate coverage,
  score distribution, method settings, and deterministic input/output hashes.

## Frozen result

The complete build scored all 149 movies in the strict text sample. Of these,
144 have one or more lexicon hits and five have none. The observed movie score
range is `-1.0` to `1.0`, with a median of `0.5` and a mean of `0.458346`.
Mean lexicon coverage is `0.016762` of tokens. These values describe feature
availability and distribution only; they are not evidence of predictive gain.

The numeric feature-table SHA-256 is
`38756fc53fc2c5d2a5ac9da95322a331c7f365475f26eec3d3b5f141251a378c`.
Its recorded input hash exactly matches the strict sample frozen in the prior
step.

This step creates features only. It does not select Ridge hyperparameters,
compare prediction errors, or decide whether sentiment improves the model.
