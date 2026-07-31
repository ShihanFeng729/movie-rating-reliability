from __future__ import annotations

import csv
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.demo_data import (  # noqa: E402
    DEMO_MOVIE_COUNT,
    build_demo_movies,
    write_demo_csv,
)


class DemoDataTests(unittest.TestCase):
    def test_default_generation_is_deterministic(self) -> None:
        self.assertEqual(build_demo_movies(), build_demo_movies())

    def test_demo_contains_complete_and_incomplete_records(self) -> None:
        movies = build_demo_movies()

        self.assertEqual(len(movies), DEMO_MOVIE_COUNT)
        self.assertEqual(len({movie.movie_id for movie in movies}), len(movies))
        self.assertEqual(len({movie.title for movie in movies}), len(movies))
        self.assertTrue(any(movie.is_complete for movie in movies))
        self.assertTrue(any(not movie.is_complete for movie in movies))

    def test_available_ratings_and_counts_are_valid(self) -> None:
        for movie in build_demo_movies():
            ratings = (
                movie.tmdb_rating_10,
                movie.imdb_rating_10,
                movie.movielens_rating_10,
            )
            counts = (
                movie.tmdb_vote_count,
                movie.imdb_vote_count,
                movie.movielens_rating_count,
            )
            for rating in ratings:
                if rating is not None:
                    self.assertGreaterEqual(rating, 1.0)
                    self.assertLessEqual(rating, 10.0)
            for count in counts:
                if count is not None:
                    self.assertGreater(count, 0)

    def test_csv_round_trip_has_expected_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "movie_ratings.csv"
            write_demo_csv(output)

            with output.open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))

            self.assertEqual(len(rows), DEMO_MOVIE_COUNT)
            self.assertEqual(rows[0]["movie_id"], "demo_001")
            self.assertIn(rows[0]["is_complete"], {"True", "False"})

    def test_too_few_movies_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_demo_movies(movie_count=2)
