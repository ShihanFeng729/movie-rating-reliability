from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.demo_pipeline import (  # noqa: E402
    run_demo_pipeline,
    summarize_demo_csv,
)


class DemoPipelineTests(unittest.TestCase):
    def test_pipeline_creates_valid_data_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            summary = run_demo_pipeline(project_root)
            data_path = project_root / "data" / "demo" / "movie_ratings.csv"
            report_path = (
                project_root / "reports" / "generated" / "demo_summary.json"
            )

            self.assertTrue(data_path.exists())
            self.assertTrue(report_path.exists())
            self.assertEqual(summary["row_count"], 30)
            self.assertEqual(summary["complete_row_count"], 25)
            self.assertEqual(summary["validation_status"], "passed")
            self.assertEqual(
                json.loads(report_path.read_text(encoding="utf-8"))["row_count"],
                30,
            )

    def test_duplicate_movie_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.csv"
            self._write_rows(
                path,
                [
                    self._row("same", "First"),
                    self._row("same", "Second"),
                ],
            )

            with self.assertRaisesRegex(ValueError, "duplicate movie IDs"):
                summarize_demo_csv(path)

    def test_out_of_range_rating_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.csv"
            row = self._row("one", "First")
            row["tmdb_rating_10"] = "11"
            self._write_rows(path, [row])

            with self.assertRaisesRegex(ValueError, "outside 1–10"):
                summarize_demo_csv(path)

    @staticmethod
    def _row(movie_id: str, title: str) -> dict[str, str]:
        return {
            "movie_id": movie_id,
            "title": title,
            "tmdb_rating_10": "7.0",
            "imdb_rating_10": "7.1",
            "movielens_rating_10": "6.9",
        }

    @staticmethod
    def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
