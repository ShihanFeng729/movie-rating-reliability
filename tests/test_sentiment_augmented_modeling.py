from __future__ import annotations

import csv
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.sentiment_augmented_modeling import (  # noqa: E402
    evaluate_sentiment_augmented_ridge,
)


RATING_FIELDS = [
    "movielens_id", "imdb_id", "tmdb_id", "release_year", "genres",
    "tmdb_rating_10", "tmdb_vote_count", "imdb_rating_10",
    "movielens_rating_10", "movielens_rating_count",
]
FEATURE_FIELDS = [
    "movielens_id", "imdb_id", "tmdb_id", "sentiment_score",
]


class SentimentAugmentedModelingTests(unittest.TestCase):
    def _write_fixture(self, root: Path) -> tuple[Path, Path, Path]:
        ratings = root / "ratings.csv"
        with ratings.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=RATING_FIELDS)
            writer.writeheader()
            for index in range(12):
                writer.writerow({
                    "movielens_id": str(index + 1), "imdb_id": f"tt{index + 1}",
                    "tmdb_id": str(100 + index), "release_year": str(2000 + index),
                    "genres": "Drama,Comedy",
                    "tmdb_rating_10": str(5.0 + index * 0.12),
                    "tmdb_vote_count": str(100 + index * 10),
                    "imdb_rating_10": str(5.2 + index * 0.1),
                    "movielens_rating_10": str(5.1 + index * 0.11),
                    "movielens_rating_count": str(200 + index * 10),
                })
        training = root / "training.csv"
        test = root / "test.csv"
        for path, indices in ((training, (0, 2, 4, 6)), (test, (9, 11))):
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FEATURE_FIELDS)
                writer.writeheader()
                for index in indices:
                    writer.writerow({
                        "movielens_id": str(index + 1),
                        "imdb_id": f"tt{index + 1}",
                        "tmdb_id": str(100 + index),
                        "sentiment_score": str((index - 5) / 10),
                    })
        return ratings, training, test

    def test_augmented_model_preserves_partitions_and_train_only_preprocessing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ratings, training, test = self._write_fixture(root)
            result = evaluate_sentiment_augmented_ridge(
                ratings, training, test, root / "enriched.csv",
                test_fraction=0.25, minimum_test_movies=3,
            )
            self.assertEqual(result["train_movie_count"], 9)
            self.assertEqual(result["test_movie_count"], 2)
            self.assertEqual(result["training_sentiment_available_count"], 4)
            self.assertEqual(result["training_sentiment_missing_count"], 5)
            self.assertEqual(result["extra_numeric_fields"], [
                "sentiment_score", "sentiment_available",
            ])
            self.assertTrue(result["sentiment_feature_used_by_model"])
            self.assertFalse(result["outer_test_used_for_sentiment_preprocessing"])
            coefficients = result["coefficients_at_selected_alpha"]
            self.assertIn("sentiment_score_standardized", coefficients)
            self.assertIn("sentiment_available_standardized", coefficients)

    def test_rejects_training_feature_from_outer_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ratings, training, test = self._write_fixture(root)
            with training.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FEATURE_FIELDS)
                writer.writerow({
                    "movielens_id": "10", "imdb_id": "tt10", "tmdb_id": "109",
                    "sentiment_score": "0.5",
                })
            with self.assertRaisesRegex(ValueError, "outside V1 training"):
                evaluate_sentiment_augmented_ridge(
                    ratings, training, test, root / "enriched.csv",
                    test_fraction=0.25, minimum_test_movies=3,
                )

    def test_rejects_stable_id_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ratings, training, test = self._write_fixture(root)
            test.write_text(
                test.read_text(encoding="utf-8").replace("tt10", "tt-wrong"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Stable ID mismatch"):
                evaluate_sentiment_augmented_ridge(
                    ratings, training, test, root / "enriched.csv",
                    test_fraction=0.25, minimum_test_movies=3,
                )


if __name__ == "__main__":
    unittest.main()
