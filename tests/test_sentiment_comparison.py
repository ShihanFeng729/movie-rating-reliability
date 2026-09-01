from __future__ import annotations

import csv
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.sentiment_comparison import (  # noqa: E402
    compare_sentiment_models,
)


class SentimentComparisonTests(unittest.TestCase):
    def _reports_and_features(
        self, root: Path
    ) -> tuple[dict[str, object], dict[str, object], Path]:
        base_rows = []
        augmented_rows = []
        features = root / "features.csv"
        fields = ["movielens_id", "review_count", "token_count", "lexicon_hits"]
        with features.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for index, year in enumerate(range(2015, 2023), start=1):
                actual = 5.0 + index * 0.1
                base_rows.append({
                    "movielens_id": str(index), "release_year": year,
                    "actual": actual, "prediction": actual + 0.2,
                })
                augmented_error = 0.1 if year <= 2020 else 0.3
                augmented_rows.append({
                    "movielens_id": str(index), "release_year": year,
                    "actual": actual, "prediction": actual + augmented_error,
                })
                writer.writerow({
                    "movielens_id": str(index), "review_count": 2,
                    "token_count": 100, "lexicon_hits": 0 if index == 1 else 3,
                })
        return (
            {"outer_test_predictions": base_rows},
            {"outer_test_predictions": augmented_rows},
            features,
        )

    def test_reports_fixed_groups_and_directions_without_deciding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base, augmented, features = self._reports_and_features(Path(directory))
            result = compare_sentiment_models(
                base, augmented, features,
                full_outer_test_count=10, training_movie_count=20,
                training_sentiment_available_count=8,
            )
            self.assertEqual(result["comparison_movie_count"], 8)
            self.assertEqual(result["time_group_count"], 4)
            self.assertEqual(result["time_groups_with_mae_improvement"], 3)
            self.assertEqual(
                [row["mae_direction"] for row in result["predefined_time_groups"]],
                ["improved", "improved", "improved", "worsened"],
            )
            self.assertEqual(result["test_review_count_total"], 16)
            self.assertEqual(result["test_movies_without_lexicon_hits"], 1)
            self.assertFalse(result["success_decision_applied"])

    def test_rejects_different_movie_sets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base, augmented, features = self._reports_and_features(Path(directory))
            augmented["outer_test_predictions"] = augmented["outer_test_predictions"][:-1]
            with self.assertRaisesRegex(ValueError, "movie IDs differ"):
                compare_sentiment_models(base, augmented, features)

    def test_rejects_outcome_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base, augmented, features = self._reports_and_features(Path(directory))
            augmented["outer_test_predictions"][0]["actual"] = 9.0
            with self.assertRaisesRegex(ValueError, "Outcome or year mismatch"):
                compare_sentiment_models(base, augmented, features)


if __name__ == "__main__":
    unittest.main()
