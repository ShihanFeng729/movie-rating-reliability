# Matching and reliability methodology

## Matching policy

The project uses conservative, auditable matching:

1. Match on a shared IMDb or TMDB identifier when one unique candidate exists.
2. Otherwise, match an exactly normalized title within one release year.
3. Reject multiple candidates as ambiguous.
4. Do not match on title alone when a release year is missing.

IMDb identifiers from MovieLens `links.csv` are normalized by adding the `tt`
prefix and left-padding the numeric portion to at least seven digits. Title
normalization removes casing, accents, punctuation, and repeated whitespace.

This policy favors precision over match count. Title/year matches are marked
as medium confidence and should be reviewed before a final real-data analysis.

## Pairwise rating metrics

All platform ratings must first be represented on a common 1–10 scale. For each
platform pair, rows missing either rating are excluded only from that pair.

- **Overlap count and coverage:** show how much comparable data supports a
  metric.
- **Mean difference (left minus right):** estimates directional platform bias.
- **Mean absolute error (MAE):** measures typical disagreement without allowing
  positive and negative differences to cancel.
- **Pearson correlation:** measures linear association.
- **Spearman correlation:** measures monotonic rank association and uses average
  ranks for tied values.
- **95% paired percentile-bootstrap intervals:** resample matched movie pairs
  together, with replacement, using 2,000 deterministic resamples.

Correlation is not agreement. Two platforms can rank movies almost identically
while one consistently rates every movie higher, so bias and MAE must be read
alongside correlation.

## Current limitations

- The demo sample is synthetic and too small for broad conclusions.
- Bootstrap intervals describe sampling uncertainty under the observed demo
  distribution; they do not correct matching or platform-selection bias.
- The current implementation reports effect sizes and intervals, not p-values.
- Real-data title/year matches require review and match-quality reporting.

## References

- [SciPy Pearson correlation documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html)
- [SciPy Spearman correlation documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html)
- [SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
