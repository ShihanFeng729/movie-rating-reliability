from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.tmdb_candidate_collection import (  # noqa: E402
    collect_candidate_details,
)


FIELDS = [
    "movielens_id", "imdb_id", "tmdb_id", "title", "release_year", "genres",
    "movielens_rating_10", "movielens_rating_count", "imdb_rating_10",
    "imdb_vote_count", "release_decade", "movielens_rating_count_band",
]


class FakeClient:
    def __init__(self, fail_ids: set[int] | None = None) -> None:
        self.calls: list[int] = []
        self.fail_ids = fail_ids or set()

    def movie_details(self, tmdb_id: int, **kwargs: object):
        del kwargs
        self.calls.append(tmdb_id)
        if tmdb_id in self.fail_ids:
            raise OSError("temporary failure")
        return (
            {
                "id": tmdb_id,
                "title": f"TMDB {tmdb_id}",
                "release_date": "2000-01-01",
                "vote_average": 7.25,
                "vote_count": 100 if tmdb_id != 102 else 49,
                "popularity": 12.5,
                "genres": [{"id": 1, "name": "Drama"}],
            },
            {"fetched_at_utc": "2026-08-12T00:00:00+00:00"},
        )


def write_candidates(path: Path, ids: list[int]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        for offset, tmdb_id in enumerate(ids, start=1):
            writer.writerow(
                {
                    "movielens_id": offset,
                    "imdb_id": f"tt{offset:07d}",
                    "tmdb_id": tmdb_id,
                    "title": f"Movie {offset}",
                    "release_year": 2000,
                    "genres": "Drama",
                    "movielens_rating_10": 7.0,
                    "movielens_rating_count": 200,
                    "imdb_rating_10": 7.1,
                    "imdb_vote_count": 1000,
                    "release_decade": 2000,
                    "movielens_rating_count_band": "200-999",
                }
            )


class CandidateCollectionTests(unittest.TestCase):
    def run_collection(self, root: Path, client: FakeClient, **kwargs: object):
        return collect_candidate_details(
            client,
            root / "candidates.csv",
            root / "raw",
            root / "processed.csv",
            root / "summary.json",
            tmdb_minimum_votes=50,
            target_complete=2,
            minimum_complete=1,
            expected_candidates=3,
            **kwargs,
        )

    def test_collects_resumes_and_filters_vote_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_candidates(root / "candidates.csv", [101, 102, 103])
            first_client = FakeClient()
            summary = self.run_collection(root, first_client)

            self.assertEqual(first_client.calls, [101, 102, 103])
            self.assertEqual(summary["complete_movie_count"], 2)
            self.assertEqual(summary["validation_status"], "target_met")
            rows = list(csv.DictReader((root / "processed.csv").open()))
            self.assertEqual([row["tmdb_id"] for row in rows], ["101", "103"])
            self.assertEqual(rows[0]["tmdb_genres"], "Drama")

            second_client = FakeClient()
            resumed = self.run_collection(root, second_client)
            self.assertEqual(second_client.calls, [])
            self.assertEqual(resumed["reused_this_run"], 3)

    def test_records_failure_without_losing_successes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_candidates(root / "candidates.csv", [101, 102, 103])
            summary = self.run_collection(root, FakeClient({103}))

            self.assertEqual(summary["failed_this_run"], 1)
            self.assertEqual(summary["failures"][0]["tmdb_id"], 103)
            self.assertTrue((root / "raw" / "items" / "101.json").exists())

    def test_rejects_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_candidates(root / "candidates.csv", [101, 101, 103])
            with self.assertRaisesRegex(ValueError, "duplicate TMDB IDs"):
                self.run_collection(root, FakeClient())

    def test_limit_keeps_collection_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_candidates(root / "candidates.csv", [101, 102, 103])
            client = FakeClient()
            summary = self.run_collection(root, client, limit=1)
            self.assertEqual(client.calls, [101])
            self.assertEqual(summary["attempted_this_run"], 1)
            self.assertEqual(summary["validation_status"], "minimum_met")


if __name__ == "__main__":
    unittest.main()
