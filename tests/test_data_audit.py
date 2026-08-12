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

from movie_rating_reliability.data_audit import audit_v1_dataset  # noqa: E402


class DataAuditTests(unittest.TestCase):
    def test_audit_records_rejections_review_and_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_path = root / "candidates.csv"
            candidate_fields = [
                "movielens_id", "imdb_id", "tmdb_id", "title", "release_year"
            ]
            with candidate_path.open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=candidate_fields)
                writer.writeheader()
                for index in range(1000):
                    writer.writerow({
                        "movielens_id": index + 1,
                        "imdb_id": f"tt{index + 1:07d}",
                        "tmdb_id": index + 101,
                        "title": f"Movie {index + 1}",
                        "release_year": 2000,
                    })
            items = root / "items"
            items.mkdir()
            for index in range(1000):
                tmdb_id = index + 101
                vote_count = 49 if index == 1 else 100
                imdb_id = "tt9999999" if index == 2 else f"tt{index + 1:07d}"
                (items / f"{tmdb_id}.json").write_text(json.dumps({
                    "payload": {
                        "id": tmdb_id, "imdb_id": imdb_id,
                        "vote_count": vote_count, "title": f"Movie {index + 1}",
                        "release_date": "2000-01-01",
                    },
                    "request": {"fetched_at_utc": "2026-08-12T00:00:00+00:00"},
                }))
            processed_path = root / "processed.csv"
            processed_fields = [
                "movielens_id", "imdb_id", "tmdb_id", "movielens_rating_10",
                "imdb_rating_10", "tmdb_rating_10",
            ]
            with processed_path.open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=processed_fields)
                writer.writeheader()
                for index in range(1000):
                    if index == 1:
                        continue
                    writer.writerow({
                        "movielens_id": index + 1,
                        "imdb_id": f"tt{index + 1:07d}",
                        "tmdb_id": index + 101,
                        "movielens_rating_10": 7,
                        "imdb_rating_10": 7,
                        "tmdb_rating_10": 7,
                    })
            collection = root / "collection.json"
            collection.write_text(json.dumps({"generated_at_utc": "2026-08-12T00:00:00Z"}))
            source = root / "source.json"
            source.write_text(json.dumps({"api_source": {"collection_sha256": "a" * 64}}))
            report_path = root / "report.json"
            review_path = root / "review.csv"
            rejection_path = root / "reject.csv"
            freeze_path = root / "freeze.json"

            report = audit_v1_dataset(
                candidate_path=candidate_path,
                items_dir=items,
                processed_path=processed_path,
                collection_summary_path=collection,
                source_manifest_path=source,
                report_path=report_path,
                review_path=review_path,
                rejection_path=rejection_path,
                freeze_path=freeze_path,
                generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
            )

            self.assertEqual(report["rejected_count"], 1)
            self.assertEqual(report["manual_review_count"], 1)
            self.assertEqual(report["validation_status"], "failed")
            self.assertEqual(len(list(csv.DictReader(review_path.open()))), 1)
            freeze = json.loads(freeze_path.read_text())
            self.assertEqual(freeze["row_count"], 999)
            self.assertEqual(len(freeze["processed_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
