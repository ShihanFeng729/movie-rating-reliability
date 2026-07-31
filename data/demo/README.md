# Demo data

`movie_ratings.csv` is a small, fictional dataset for running and reviewing the
project without an IMDb/MovieLens download or TMDB API token.

Important characteristics:

- all titles and identifiers are invented
- ratings are synthetic and must not be interpreted as real platform data
- all platform ratings use a common 1–10 scale
- a small number of missing values deliberately represent platform coverage
  and matching gaps
- generation is deterministic, using seed `510`

Regenerate the CSV from the repository root:

```bash
python3 scripts/generate_demo_data.py
```

The generation logic lives in `src/movie_rating_reliability/demo_data.py`, and
automated checks live in `tests/test_demo_data.py`.
