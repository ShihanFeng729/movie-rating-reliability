# Movie Rating Reliability

Cross-platform movie rating reliability analysis with reproducible data
pipelines and interpretable prediction models.

## Status

The data download and API snapshot workflows are implemented. Analysis and
modeling are not implemented yet.

This is an independent post-course redevelopment of an earlier academic
prototype. It uses a new Git history and will be redesigned for reproducibility,
testing, transparent evaluation, and portfolio presentation.

## Core questions

1. How consistent are ratings across TMDB, IMDb, and MovieLens?
2. Do platforms show stable patterns of rating higher or lower than one another?
3. How do vote count, release year, genre, and popularity relate to differences?
4. Does review sentiment provide additional explanatory value?
5. Can an interpretable baseline predict a rating or rating range with clearly
   reported error?

The project will not treat correlation alone as proof of reliability or claim
that any platform provides a single "true" rating.

## Project structure

```text
movie-rating-reliability/
├── data/        # Local data lifecycle; real datasets are ignored
├── docs/        # Methodology, decisions, licenses, and attribution
├── notebooks/   # Exploration and presentation using functions from src/
├── reports/     # Reproducible summaries and generated figures
├── scripts/     # Small download and maintenance entry points
├── src/         # Reusable Python package and core project logic
└── tests/       # Automated tests using synthetic fixtures
```

Each directory contains a short README explaining its role.

## Download the source data

No Python environment or extra package is required for this step. From the
repository's top-level folder, run:

```bash
python3 scripts/download_data.py
```

This downloads IMDb plus the small MovieLens development dataset. The files
stay under `data/external/` and are not committed to GitHub. When the analysis
pipeline is ready for a full-scale run, choose the stable MovieLens 32M file:

```bash
python3 scripts/download_data.py --movielens research
```

See [`data/README.md`](data/README.md) for the folder meanings and download
options.

## Collect a TMDB snapshot

After obtaining a TMDB API Read Access Token, keep it outside the code and make
it available only in the terminal session:

```bash
export TMDB_BEARER_TOKEN="your_api_read_access_token"
python3 scripts/collect_tmdb.py --pages 1
```

The collector caches responses, retries temporary API errors, respects TMDB
rate-limit responses, and records UTC collection times. Real tokens, API
caches, and raw snapshots are excluded from Git. See `.env.example` for the
expected variable name.

## Run without credentials

The repository includes a small fictional dataset so the project can be
reviewed without API keys or large downloads:

```bash
python3 scripts/generate_demo_data.py
```

This recreates `data/demo/movie_ratings.csv` deterministically. Its movie
titles and ratings are synthetic and are clearly separated from real research
data.

## Planned data sources

- [TMDB API](https://developer.themoviedb.org/docs/getting-started)
- [IMDb non-commercial datasets](https://developer.imdb.com/non-commercial-datasets/)
- [MovieLens datasets](https://grouplens.org/datasets/movielens/)

Raw licensed datasets, research-generated outputs, API keys, and local
environment files will not be committed. The small fictional demo dataset is
the explicit exception.

## Development approach

This project uses an AI-assisted, human-directed development workflow. Project
decisions, code behavior, tests, data validation, and analytical conclusions
will be reviewed and documented step by step.

## Earlier prototype

The original course submission remains preserved separately at
[dsci510_spring2026_final_project](https://github.com/ShihanFeng729/dsci510_spring2026_final_project).
All portfolio-oriented redevelopment will happen in this repository.
