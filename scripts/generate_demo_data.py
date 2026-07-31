#!/usr/bin/env python3
"""Generate the tracked, API-free demonstration dataset."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.demo_data import (  # noqa: E402
    build_demo_movies,
    write_demo_csv,
)


def main() -> None:
    output_path = PROJECT_ROOT / "data" / "demo" / "movie_ratings.csv"
    movies = build_demo_movies()
    write_demo_csv(output_path, movies)
    complete_count = sum(movie.is_complete for movie in movies)
    print(
        f"Saved {len(movies)} fictional movies to {output_path} "
        f"({complete_count} complete across all three platforms)."
    )


if __name__ == "__main__":
    main()
