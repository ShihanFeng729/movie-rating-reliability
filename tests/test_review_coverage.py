from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.review_coverage import (  # noqa: E402
    audit_review_coverage,
    temporal_holdout_rows,
)


class FakeReviewClient:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def movie_reviews(
        self, tmdb_id: int, *, page: int, language: str, refresh: bool
    ) -> tuple[dict[str, object], dict[str, str]]:
        del page, language, refresh
        self.calls.append(tmdb_id)
        results = [] if tmdb_id % 2 else [
            {
                "content": "Useful review", "iso_639_1": "en",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-02T00:00:00Z",
            },
            {"content": " ", "iso_639_1": "fr"},
        ]
        return (
            {"id": tmdb_id, "results": results, "total_results": len(results)},
            {"fetched_at_utc": "2026-08-13T00:00:00+00:00"},
        )


class ReviewCoverageTests(unittest.TestCase):
    def _write_dataset(self, path: Path, count: int = 10) -> None:
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(
                file, fieldnames=["movielens_id", "tmdb_id", "release_year"]
            )
            writer.writeheader()
            for index in range(count):
                writer.writerow({
                    "movielens_id": str(index + 1),
                    "tmdb_id": str(100 + index),
                    "release_year": str(2000 + index),
                })

    def test_holdout_matches_newest_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.csv"
            self._write_dataset(path)
            rows = temporal_holdout_rows(
                path, test_fraction=0.2, minimum_test_movies=2
            )
            self.assertEqual([row["release_year"] for row in rows], ["2008", "2009"])

    def test_audit_summarizes_coverage_without_review_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "data.csv"
            self._write_dataset(path)
            client = FakeReviewClient()
            summary = audit_review_coverage(
                client,
                path,
                root / "raw",
                root / "summary.json",
                limit=2,
                minimum_test_movies=2,
            )
            self.assertEqual(summary["fixed_holdout_movie_count"], 2)
            self.assertEqual(summary["audited_movie_count"], 2)
            self.assertEqual(summary["text_covered_movie_count"], 1)
            self.assertEqual(summary["language_movie_counts"], {"en": 1})
            covered = next(
                item for item in summary["movie_audits"]
                if item["nonempty_review_count"]
            )
            self.assertEqual(covered["reviews_with_created_at"], 1)
            self.assertFalse(summary["raw_review_text_published"])
            self.assertNotIn("Useful review", json.dumps(summary))

            audit_review_coverage(
                client, path, root / "raw", root / "summary.json", limit=2,
                minimum_test_movies=2,
            )
            self.assertEqual(client.calls, [108, 109])


if __name__ == "__main__":
    unittest.main()
