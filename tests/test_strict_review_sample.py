from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.strict_review_sample import (  # noqa: E402
    build_strict_review_sample,
)


class StrictReviewSampleTests(unittest.TestCase):
    def test_freeze_filters_time_and_language_without_author_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ratings = root / "ratings.csv"
            raw = root / "raw"
            raw.mkdir()
            with ratings.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "movielens_id", "imdb_id", "tmdb_id", "release_year",
                ])
                writer.writeheader()
                writer.writerow({
                    "movielens_id": "7", "imdb_id": "tt0000042",
                    "tmdb_id": "42", "release_year": "2022",
                })
            record = {"payload": {"id": 42, "results": [
                {
                    "author": "private-name",
                    "content": "Kept English review text for the first movie.",
                    "created_at": "2023-01-01T00:00:00Z",
                },
                {
                    "content": "Texto que se debe excluir.",
                    "created_at": "2023-02-01T00:00:00Z",
                },
                {
                    "content": "English text written too late.",
                    "created_at": "2024-01-01T00:00:00Z",
                },
                {"content": "Missing timestamp text."},
            ]}}
            (raw / "42.json").write_text(json.dumps(record), encoding="utf-8")
            labels = {
                "Kept English review text for the first movie.": "en",
                "Texto que se debe excluir.": "es",
            }
            output = root / "sample.jsonl"
            summary_path = root / "summary.json"
            summary = build_strict_review_sample(
                ratings, raw, output, summary_path,
                cutoff=datetime(2023, 10, 13, tzinfo=timezone.utc),
                language_detector=labels.__getitem__,
            )
            row = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(row["tmdb_id"], 42)
            self.assertEqual(row["review_count"], 1)
            self.assertIn("Kept English", row["aggregated_review_text"])
            self.assertNotIn("author", row)
            self.assertNotIn("private-name", output.read_text(encoding="utf-8"))
            self.assertEqual(summary["source_nonempty_review_count"], 4)
            self.assertEqual(summary["reviews_missing_created_at"], 1)
            self.assertEqual(summary["reviews_after_cutoff"], 1)
            self.assertEqual(summary["reviews_rejected_by_language"], 1)
            self.assertEqual(summary["frozen_review_count"], 1)
            self.assertNotIn("Kept English", summary_path.read_text(encoding="utf-8"))

    def test_repeated_build_has_stable_output_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ratings = root / "ratings.csv"
            raw = root / "raw"
            raw.mkdir()
            ratings.write_text(
                "movielens_id,imdb_id,tmdb_id,release_year\n1,tt1,9,2020\n",
                encoding="utf-8",
            )
            payload = {"payload": {"results": [
                {"content": "Second text.", "created_at": "2023-01-02T00:00:00Z"},
                {"content": "First text.", "created_at": "2023-01-01T00:00:00Z"},
            ]}}
            (raw / "9.json").write_text(json.dumps(payload), encoding="utf-8")
            hashes = []
            for suffix in ("a", "b"):
                summary = build_strict_review_sample(
                    ratings, raw, root / f"{suffix}.jsonl", root / f"{suffix}.json",
                    cutoff=datetime(2023, 10, 13, tzinfo=timezone.utc),
                    language_detector=lambda _: "en",
                )
                hashes.append(summary["output_sha256"])
            self.assertEqual(hashes[0], hashes[1])
            self.assertEqual(
                (root / "a.jsonl").read_bytes(), (root / "b.jsonl").read_bytes()
            )

    def test_rejects_unmatched_stable_tmdb_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            raw.mkdir()
            (root / "ratings.csv").write_text(
                "movielens_id,imdb_id,tmdb_id,release_year\n1,tt1,8,2020\n",
                encoding="utf-8",
            )
            (raw / "9.json").write_text(
                json.dumps({"payload": {"results": []}}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "absent"):
                build_strict_review_sample(
                    root / "ratings.csv", raw, root / "out.jsonl", root / "out.json",
                    cutoff=datetime(2023, 10, 13, tzinfo=timezone.utc),
                    language_detector=lambda _: "en",
                )


if __name__ == "__main__":
    unittest.main()
