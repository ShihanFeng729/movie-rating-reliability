from __future__ import annotations

import csv
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.reliability_analysis import (  # noqa: E402
    analyze_reliability_segments,
)


class ReliabilityAnalysisTests(unittest.TestCase):
    def test_grouped_and_sensitivity_results_are_generated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ratings.csv"
            fields = [
                "release_decade", "genres", "movielens_rating_count_band",
                "tmdb_popularity", "tmdb_vote_count", "imdb_vote_count",
                "movielens_rating_count", "tmdb_rating_10", "imdb_rating_10",
                "movielens_rating_10",
            ]
            with path.open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                for index in range(12):
                    writer.writerow({
                        "release_decade": 2000 if index < 6 else 2010,
                        "genres": "Drama,Comedy" if index % 2 else "Action",
                        "movielens_rating_count_band": "200-999",
                        "tmdb_popularity": index + 1,
                        "tmdb_vote_count": 600,
                        "imdb_vote_count": 2000,
                        "movielens_rating_count": 300,
                        "tmdb_rating_10": 5 + index / 10,
                        "imdb_rating_10": 5.1 + index / 10,
                        "movielens_rating_10": 5.2 + index / 10,
                    })
            result = analyze_reliability_segments(path, minimum_group_size=3)
            self.assertEqual(len(result["grouped_results"]["release_decade"]), 2)
            self.assertEqual(len(result["sensitivity_results"]), 3)
            self.assertFalse(result["matching_sensitivity"]["available"])
            self.assertIn("agreement", result["interpretation_boundaries"])
