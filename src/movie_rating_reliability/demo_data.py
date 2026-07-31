"""Generate a small synthetic cross-platform movie-rating dataset."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
from pathlib import Path
import random


DEMO_SEED = 510
DEMO_MOVIE_COUNT = 30
GENRES = ("Action", "Comedy", "Drama", "Documentary", "Horror", "Sci-Fi")
TITLE_ADJECTIVES = (
    "Amber",
    "Broken",
    "Crimson",
    "Distant",
    "Electric",
    "Hidden",
    "Last",
    "Quiet",
    "Silver",
    "Winter",
)
TITLE_NOUNS = ("Archive", "Bridge", "City", "Echo", "Garden", "Orbit")


@dataclass(frozen=True)
class DemoMovie:
    """One analysis-ready synthetic movie record."""

    movie_id: str
    title: str
    release_year: int
    genre: str
    tmdb_rating_10: float | None
    tmdb_vote_count: int | None
    imdb_rating_10: float | None
    imdb_vote_count: int | None
    movielens_rating_10: float | None
    movielens_rating_count: int | None
    is_complete: bool


def _bounded_rating(value: float) -> float:
    return round(min(10.0, max(1.0, value)), 1)


def build_demo_movies(
    *,
    seed: int = DEMO_SEED,
    movie_count: int = DEMO_MOVIE_COUNT,
) -> list[DemoMovie]:
    """Return deterministic fictional movies with realistic rating differences."""

    if movie_count < 3:
        raise ValueError("movie_count must be at least 3.")

    rng = random.Random(seed)
    movies: list[DemoMovie] = []

    for index in range(movie_count):
        latent_quality = rng.uniform(3.8, 9.0)
        tmdb_rating = _bounded_rating(latent_quality + 0.20 + rng.gauss(0, 0.35))
        imdb_rating = _bounded_rating(latent_quality - 0.05 + rng.gauss(0, 0.25))
        movielens_rating = _bounded_rating(
            latent_quality + 0.10 + rng.gauss(0, 0.45)
        )

        tmdb_count = rng.randint(80, 55_000)
        imdb_count = rng.randint(500, 900_000)
        movielens_count = rng.randint(20, 18_000)

        # Predictable missingness mirrors coverage gaps in real joined data.
        if index % 10 == 7:
            movielens_rating = None
            movielens_count = None
        if index % 15 == 11:
            tmdb_rating = None
            tmdb_count = None

        title = (
            f"{TITLE_ADJECTIVES[index % len(TITLE_ADJECTIVES)]} "
            f"{TITLE_NOUNS[(index // len(TITLE_ADJECTIVES)) % len(TITLE_NOUNS)]}"
        )
        complete = all(
            value is not None
            for value in (tmdb_rating, imdb_rating, movielens_rating)
        )
        movies.append(
            DemoMovie(
                movie_id=f"demo_{index + 1:03d}",
                title=title,
                release_year=rng.randint(1980, 2025),
                genre=GENRES[index % len(GENRES)],
                tmdb_rating_10=tmdb_rating,
                tmdb_vote_count=tmdb_count,
                imdb_rating_10=imdb_rating,
                imdb_vote_count=imdb_count,
                movielens_rating_10=movielens_rating,
                movielens_rating_count=movielens_count,
                is_complete=complete,
            )
        )

    return movies


def write_demo_csv(path: Path, movies: list[DemoMovie] | None = None) -> Path:
    """Write demo records as a portable CSV and return its path."""

    records = movies if movies is not None else build_demo_movies()
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(DemoMovie.__dataclass_fields__)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for movie in records:
            writer.writerow(asdict(movie))
    return path
