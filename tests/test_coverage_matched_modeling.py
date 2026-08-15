from __future__ import annotations

import csv
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.coverage_matched_modeling import (  # noqa: E402
    evaluate_coverage_matched_ridge,
)
from movie_rating_reliability.modeling import evaluate_temporal_holdout  # noqa: E402


RATING_FIELDS = [
    "movielens_id", "imdb_id", "tmdb_id", "release_year", "genres",
    "tmdb_rating_10", "tmdb_vote_count", "imdb_rating_10",
    "movielens_rating_10", "movielens_rating_count",
]
FEATURE_FIELDS = [
    "movielens_id", "imdb_id", "tmdb_id", "sentiment_score",
]


class CoverageMatchedModelingTests(unittest.TestCase):
    def _write_fixture(self, root: Path) -> tuple[Path, Path]:
        ratings_path = root / "ratings.csv"
        with ratings_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=RATING_FIELDS)
            writer.writeheader()
            for index in range(12):
                writer.writerow({
                    "movielens_id": str(index + 1),
                    "imdb_id": f"tt{index + 1}",
                    "tmdb_id": str(100 + index),
                    "release_year": str(2000 + index),
                    "genres": "Drama,Comedy",
                    "tmdb_rating_10": str(5.0 + index * 0.12),
                    "tmdb_vote_count": str(100 + index * 10),
                    "imdb_rating_10": str(5.2 + index * 0.1),
                    "movielens_rating_10": str(5.1 + index * 0.11),
                    "movielens_rating_count": str(200 + index * 10),
                })
        features_path = root / "features.csv"
        with features_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FEATURE_FIELDS)
            writer.writeheader()
            for index in (9, 11):
                writer.writerow({
                    "movielens_id": str(index + 1),
                    "imdb_id": f"tt{index + 1}",
                    "tmdb_id": str(100 + index),
                    "sentiment_score": "0.5",
                })
        return ratings_path, features_path

    def test_uses_same_training_rows_and_only_coverage_matched_test_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ratings, features = self._write_fixture(Path(directory))
            full = evaluate_temporal_holdout(
                ratings, test_fraction=0.25, minimum_test_movies=3
            )
            matched = evaluate_coverage_matched_ridge(
                ratings, features, test_fraction=0.25, minimum_test_movies=3
            )
            self.assertEqual(full["train_movie_count"], matched["train_movie_count"])
            self.assertEqual(full["ridge_alpha"], matched["ridge_alpha"])
            self.assertEqual(matched["full_outer_test_movie_count"], 3)
            self.assertEqual(matched["test_movie_count"], 2)
            self.assertEqual(matched["coverage_movie_count"], 2)
            self.assertEqual(len(matched["coverage_movie_ids_sha256"]), 64)
            self.assertTrue(matched["outer_test_coverage_filter_applied"])
            self.assertFalse(matched["sentiment_feature_used_by_model"])

    def test_rejects_cross_platform_id_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ratings, features = self._write_fixture(Path(directory))
            text = features.read_text(encoding="utf-8").replace("tt10", "tt-wrong")
            features.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Stable ID mismatch"):
                evaluate_coverage_matched_ridge(
                    ratings, features, test_fraction=0.25, minimum_test_movies=3
                )

    def test_rejects_coverage_movie_outside_fixed_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ratings, features = self._write_fixture(Path(directory))
            with features.open("a", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=FEATURE_FIELDS)
                writer.writerow({
                    "movielens_id": "1", "imdb_id": "tt1", "tmdb_id": "100",
                    "sentiment_score": "0.2",
                })
            with self.assertRaisesRegex(ValueError, "outside the fixed temporal"):
                evaluate_coverage_matched_ridge(
                    ratings, features, test_fraction=0.25, minimum_test_movies=3
                )


if __name__ == "__main__":
    unittest.main()
