from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RepositoryPrivacyTests(unittest.TestCase):
    def test_sensitive_v1_1_artifact_paths_are_ignored_and_untracked(self) -> None:
        representative_paths = (
            ".env",
            "data/raw/tmdb/v1_reviews/example.json",
            "data/raw/tmdb/v1_1_training_reviews/example.json",
            "data/processed/v1_1_strict_review_sample.jsonl",
            "data/processed/v1_1_sentiment_features.csv",
            "data/processed/v1_1_training_sentiment_features.csv",
            "data/processed/v1_1_sentiment_enriched_ratings.csv",
            "reports/generated/v1_1_sentiment_decision.json",
        )
        for path in representative_paths:
            with self.subTest(path=path):
                ignored = subprocess.run(
                    ["git", "check-ignore", "--quiet", "--", path],
                    cwd=PROJECT_ROOT,
                    check=False,
                )
                self.assertEqual(ignored.returncode, 0, f"Path is not ignored: {path}")
                tracked = subprocess.run(
                    ["git", "ls-files", "--error-unmatch", "--", path],
                    cwd=PROJECT_ROOT,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.assertNotEqual(tracked.returncode, 0, f"Path is tracked: {path}")


if __name__ == "__main__":
    unittest.main()
