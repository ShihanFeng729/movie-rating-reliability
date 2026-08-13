# Sentiment module decision gate

## Decision status

**Conditional Go for a coverage audit; No-Go for model implementation yet.**

The rating baseline is now evaluated on an untouched temporal holdout. This
creates a defensible residual target for asking whether review language adds
information. It does not establish that enough usable text exists or that
sentiment will improve prediction.

## Candidate sources

### TMDB movie reviews — audit first

TMDB provides an official movie-reviews endpoint and is already connected to
the project through stable TMDB IDs. It is the most practical source for a
small, resumable coverage audit. Review responses must remain local, the
collection time and requested language must be recorded, and published project
content must follow TMDB attribution and usage requirements.

### IMDb reviews — exclude from V1.1 collection

The IMDb non-commercial downloadable files used by this project contain title
and aggregate rating data, not review text. IMDb lists user reviews as a
separate licensed metadata product. The project will not scrape IMDb pages or
assume those reviews are part of the existing download permission.

### MovieLens tags — contextual alternative, not sentiment text

MovieLens 32M includes user-applied short tags, not a stable corpus of review
prose. Tags may later support a separate content/context experiment, but they
should not be presented as equivalent to review sentiment.

## Coverage audit

Use the 189 movies in the fixed outer holdout as the first audit population.
This avoids changing the evaluation question after inspecting text. For each
movie, record only audit metadata in generated summaries:

- stable TMDB ID;
- number of reviews returned;
- number of non-empty reviews;
- language inferred locally in a later, separately validated step (the TMDB
  response does not provide a dependable review-language field);
- collection timestamp and endpoint parameters; and
- error or unavailable status.

Raw review bodies and author information remain local and are excluded from
Git. The audit should begin with 20–30 movies as a connection and schema check,
then continue across all 189 if the endpoint is stable.

## Predeclared decision rules

Proceed to a small V1.1 sentiment baseline only if all of the following hold:

1. at least 60% of the 189 holdout movies have one or more non-empty reviews;
2. at least 100 holdout movies are text-covered, so the comparison is not based
   on a very small subset;
3. locally validated language identification shows that a single language
   covers at least 80% of text-covered movies, or a documented multilingual
   method is chosen before modeling;
4. review collection and local retention are compatible with the source terms
   and attribution requirements; and
5. review timing can be recorded well enough to discuss possible leakage from
   reviews written after the rating snapshot.

If these conditions fail, stop the sentiment branch and preserve the negative
coverage result. Do not replace the missing evidence with a more complex model.

## Success criterion after a Go decision

The existing Ridge model remains the comparison baseline. Sentiment features
must be added within the same temporal evaluation design, with every text
processing choice learned from training data only. The extension succeeds only
if it reduces MAE on the same eligible held-out movies by at least 0.01 and the
direction of improvement is also present in at least three of four chronological
holdout subgroups. Coverage-matched Ridge metrics must be reported so that
missing reviews cannot create an unfair comparison.

## First coverage result

The fixed 189-movie outer holdout was audited successfully with zero request
failures. Of those movies, 151 have at least one non-empty first-page TMDB
review, for 79.89% coverage. This passes the predeclared minimum of both 60%
and 100 covered movies.

The API response provides review creation and update timestamps, but no
dependable language field. The decision therefore remains conditional: local
language identification must be validated, and review timestamps must be
compared with the rating snapshot boundaries before sentiment features are
implemented.

## Interpretation boundary

A successful sentiment feature would show incremental predictive information,
not prove that review tone causes platform rating differences. A failed or
inconclusive result is still informative: it would show that the available text
does not justify added complexity under this snapshot and validation design.

## Source references

- [TMDB movie reviews endpoint](https://developer.themoviedb.org/reference/movie-reviews)
- [TMDB API FAQ and attribution](https://developer.themoviedb.org/docs/faq)
- [IMDb datasets and licensed metadata](https://developer.imdb.com/)
- [MovieLens datasets](https://grouplens.org/datasets/movielens/)
