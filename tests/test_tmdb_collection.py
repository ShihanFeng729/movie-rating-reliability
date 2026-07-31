from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.tmdb_collection import (  # noqa: E402
    collect_discover_snapshot,
)


class FakeClient:
    def discover_movies(self, *, page: int, **kwargs: object):
        del kwargs
        return (
            {
                "page": page,
                "results": [{"id": page, "vote_average": 7.5}],
                "total_pages": 10,
            },
            {
                "source": "api",
                "url": f"https://api.test/discover?page={page}",
                "fetched_at_utc": "2026-07-30T00:00:00+00:00",
                "cache_path": f"cache/{page}.json",
            },
        )


class TmdbCollectionTests(unittest.TestCase):
    def test_snapshot_contains_movies_and_collection_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            collected_at = datetime(2026, 7, 30, 8, 9, 10, tzinfo=timezone.utc)

            metadata = collect_discover_snapshot(
                FakeClient(),
                output_root,
                pages=2,
                collected_at=collected_at,
            )

            snapshot_dir = output_root / "20260730T080910Z"
            records = [
                json.loads(line)
                for line in (snapshot_dir / "movies.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            saved_metadata = json.loads(
                (snapshot_dir / "metadata.json").read_text(encoding="utf-8")
            )

            self.assertEqual([record["id"] for record in records], [1, 2])
            self.assertEqual(records[0]["_source_page"], 1)
            self.assertEqual(
                records[0]["_snapshot_collected_at_utc"],
                collected_at.isoformat(),
            )
            self.assertEqual(metadata["movie_count"], 2)
            self.assertEqual(saved_metadata["requested_pages"], 2)

    def test_page_range_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                collect_discover_snapshot(
                    FakeClient(),
                    Path(directory),
                    pages=2,
                    start_page=500,
                )
