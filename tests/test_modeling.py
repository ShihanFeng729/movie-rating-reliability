from __future__ import annotations

from pathlib import Path
import sys
import unittest
import csv
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.modeling import (  # noqa: E402
    evaluate_prediction_model,
    evaluate_temporal_holdout,
    fit_ridge,
    load_model_dataset,
    predict,
    regression_metrics,
)


DEMO_PATH = PROJECT_ROOT / "data" / "demo" / "movie_ratings.csv"


class ModelingTests(unittest.TestCase):
    def test_unregularized_fit_recovers_simple_line(self) -> None:
        coefficients = fit_ridge([[0.0], [1.0], [2.0]], [1.0, 3.0, 5.0], alpha=0)

        self.assertAlmostEqual(coefficients[0], 1.0)
        self.assertAlmostEqual(coefficients[1], 2.0)
        self.assertAlmostEqual(predict(coefficients, [3.0]), 7.0)

    def test_demo_dataset_has_expected_complete_rows_and_features(self) -> None:
        dataset = load_model_dataset(DEMO_PATH)

        self.assertEqual(len(dataset.targets), 25)
        self.assertEqual(dataset.reference_genre, "Action")
        self.assertIn("tmdb_rating_10", dataset.feature_names)
        self.assertIn("genre_Sci-Fi", dataset.feature_names)
        self.assertNotIn("imdb_vote_count", dataset.feature_names)

    def test_evaluation_is_deterministic_and_auditable(self) -> None:
        first = evaluate_prediction_model(DEMO_PATH)
        second = evaluate_prediction_model(DEMO_PATH)

        self.assertEqual(first, second)
        self.assertEqual(first["evaluation_protocol"], "leave_one_out_cross_validation")
        self.assertEqual(len(first["cross_validation_predictions"]), 25)
        self.assertTrue(first["prediction_clipped_to_scale"])
        self.assertLess(
            first["model_metrics"]["mae"], first["baseline_metrics"]["mae"]
        )
        for row in first["cross_validation_predictions"]:
            self.assertGreaterEqual(row["model_prediction"], 1.0)
            self.assertLessEqual(row["model_prediction"], 10.0)

    def test_metrics_reject_constant_target(self) -> None:
        with self.assertRaisesRegex(ValueError, "constant target"):
            regression_metrics([5.0, 5.0], [4.0, 6.0])

    def test_temporal_holdout_accepts_real_v1_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "real.csv"
            fields = [
                "movielens_id", "release_year", "genres", "tmdb_rating_10",
                "tmdb_vote_count", "imdb_rating_10", "movielens_rating_10",
                "movielens_rating_count",
            ]
            with path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                for index in range(10):
                    writer.writerow({
                        "movielens_id": index + 1,
                        "release_year": 2000 + index,
                        "genres": "Drama,Comedy",
                        "tmdb_rating_10": 5 + index / 10,
                        "tmdb_vote_count": 100 + index,
                        "imdb_rating_10": 5.1 + index / 10,
                        "movielens_rating_10": 5.2 + index / 10,
                        "movielens_rating_count": 200 + index,
                    })
            result = evaluate_temporal_holdout(
                path, test_fraction=0.2, minimum_test_movies=2
            )
            self.assertEqual(result["train_movie_count"], 8)
            self.assertEqual(result["test_movie_count"], 2)
            self.assertEqual(result["test_year_min"], 2008)


if __name__ == "__main__":
    unittest.main()
