from __future__ import annotations

import csv
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.evaluation import (  # noqa: E402
    average_ranks,
    evaluate_rating_csv,
    mean_absolute_error,
    mean_difference,
    paired_bootstrap_interval,
    pearson_correlation,
    spearman_correlation,
)


class EvaluationTests(unittest.TestCase):
    def test_basic_pairwise_metrics(self) -> None:
        left = [1.0, 2.0, 3.0]
        right = [2.0, 4.0, 6.0]

        self.assertAlmostEqual(pearson_correlation(left, right), 1.0)
        self.assertAlmostEqual(spearman_correlation(left, right), 1.0)
        self.assertAlmostEqual(mean_difference(left, right), -2.0)
        self.assertAlmostEqual(mean_absolute_error(left, right), 2.0)

    def test_average_ranks_handle_ties(self) -> None:
        self.assertEqual(average_ranks([10.0, 10.0, 20.0]), [1.5, 1.5, 3.0])

    def test_constant_input_has_undefined_correlation(self) -> None:
        self.assertIsNone(pearson_correlation([1.0, 1.0], [2.0, 3.0]))
        self.assertIsNone(spearman_correlation([1.0, 1.0], [2.0, 3.0]))

    def test_bootstrap_interval_is_deterministic(self) -> None:
        left = [5.0, 6.0, 7.0, 8.0]
        right = [4.0, 6.0, 6.0, 9.0]

        first = paired_bootstrap_interval(
            left, right, mean_difference, resamples=100, seed=7
        )
        second = paired_bootstrap_interval(
            left, right, mean_difference, resamples=100, seed=7
        )

        self.assertEqual(first, second)
        self.assertLessEqual(first["lower"], first["upper"])

    def test_csv_evaluation_uses_pairwise_complete_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ratings.csv"
            rows = [
                {"tmdb_rating_10": "7", "imdb_rating_10": "6", "movielens_rating_10": "5"},
                {"tmdb_rating_10": "8", "imdb_rating_10": "7", "movielens_rating_10": ""},
                {"tmdb_rating_10": "", "imdb_rating_10": "8", "movielens_rating_10": "7"},
                {"tmdb_rating_10": "6", "imdb_rating_10": "", "movielens_rating_10": "6"},
                {"tmdb_rating_10": "9", "imdb_rating_10": "9", "movielens_rating_10": ""},
            ]
            with path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

            result = evaluate_rating_csv(path)
            counts = [
                pair["overlap_count"] for pair in result["pairwise_metrics"]
            ]

            self.assertEqual(counts, [3, 2, 2])
