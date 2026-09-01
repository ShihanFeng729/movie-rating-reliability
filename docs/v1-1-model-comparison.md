# V1.1 same-sample model comparison

The fifth V1.1 step reports the fixed base-Ridge and sentiment-Ridge evidence
without changing either model or applying the final continuation decision.

## Identity and evaluation checks

Both models use the same 752 training movies and the same 149 strict-coverage
outer-test movies. Before comparing metrics, the report verifies that every
MovieLens ID, IMDb outcome, and release year agrees row by row. The frozen
149-movie ID SHA-256 is
`5d2edc4fbf95f7a7092be613cca17b4234b2d9c57557e200701763dcd397468f`.
The generated local comparison report SHA-256 is
`6ceab11a639d52350f27e4ee410260a06f0495fcaa4a1060c51968b44c7c89c9`.

The four time groups were fixed as consecutive two-year intervals before this
report was calculated:

- 2015–2016;
- 2017–2018;
- 2019–2020; and
- 2021–2022.

## Overall comparison

| Model | MAE | RMSE | R² |
|---|---:|---:|---:|
| Coverage-matched base Ridge | 0.2040 | 0.2908 | 0.8997 |
| Sentiment-augmented Ridge | 0.2029 | 0.2881 | 0.9015 |

The sentiment model lowers MAE by `0.0011` on the common sample.

## Predefined time groups

| Release years | Movies | Base MAE | Sentiment MAE | Base − sentiment | Direction |
|---|---:|---:|---:|---:|---|
| 2015–2016 | 39 | 0.2242 | 0.2249 | -0.0007 | Worsened |
| 2017–2018 | 46 | 0.1594 | 0.1564 | 0.0030 | Improved |
| 2019–2020 | 33 | 0.2150 | 0.2163 | -0.0013 | Worsened |
| 2021–2022 | 31 | 0.2330 | 0.2300 | 0.0030 | Improved |

Two of four time groups improve and two worsen.

## Text availability and limits

- Strict test coverage is 149/189 movies, or 78.84%.
- Strict training sentiment coverage is 325/752 movies, or 43.22%.
- The test feature contains 441 reviews, averaging 2.9597 per movie.
- Test text contains 135,802 scored tokens, averaging 911.4228 per movie.
- Five test movies have text but no fixed-lexicon hits.
- Only the first TMDB review page is collected, so the text is not a complete
  review corpus.
- Training coverage is materially lower than test coverage, creating a feature
  availability difference that limits interpretation.
- The simple lexicon cannot reliably represent sarcasm, target-specific tone,
  mixed reviews, or broader context.

## Run locally

```bash
python3 scripts/report_v1_1_sentiment_comparison.py
```

The command rebuilds both models and writes the ignored aggregate-plus-local
diagnostic report to `reports/generated/v1_1_model_comparison.json`.

The separately recorded decision applies the already fixed thresholds—overall
MAE improvement of at least `0.01` and improvement in at least three of four
time groups—without modifying the sample, features, model, or grouping. See
[`v1-1-decision.md`](v1-1-decision.md).
