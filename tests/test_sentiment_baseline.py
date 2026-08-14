from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.sentiment_baseline import (  # noqa: E402
    build_sentiment_features,
    score_text,
)


class SentimentBaselineTests(unittest.TestCase):
    def test_score_is_bounded_and_interpretable(self) -> None:
        positive = score_text("A great, clever and wonderful film.")
        negative = score_text("A boring, awful mess and a waste.")
        neutral = score_text("The film follows a family through one afternoon.")
        self.assertEqual(positive["sentiment_score"], 1.0)
        self.assertEqual(positive["positive_hits"], 3)
        self.assertEqual(negative["sentiment_score"], -1.0)
        self.assertEqual(negative["negative_hits"], 4)
        self.assertEqual(neutral["sentiment_score"], 0.0)
        self.assertEqual(neutral["lexicon_hits"], 0)

    def test_negation_flips_local_word_polarity(self) -> None:
        self.assertEqual(score_text("This is not good.")["sentiment_score"], -1.0)
        self.assertEqual(score_text("This is not bad.")["sentiment_score"], 1.0)
        self.assertEqual(
            score_text("This is not really very good.")["sentiment_score"], -1.0
        )

    def test_feature_output_excludes_text_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = root / "sample.jsonl"
            sample_rows = [
                {
                    "movielens_id": "2", "imdb_id": "tt2", "tmdb_id": 20,
                    "release_year": 2021, "review_count": 1,
                    "aggregated_review_text": "A wonderful and moving film.",
                },
                {
                    "movielens_id": "1", "imdb_id": "tt1", "tmdb_id": 10,
                    "release_year": 2020, "review_count": 2,
                    "aggregated_review_text": "Not good. A boring mess.",
                },
            ]
            sample.write_text(
                "".join(json.dumps(row) + "\n" for row in sample_rows),
                encoding="utf-8",
            )
            hashes = []
            for suffix in ("a", "b"):
                output = root / f"{suffix}.csv"
                summary = build_sentiment_features(
                    sample, output, root / f"{suffix}.json"
                )
                hashes.append(summary["output_sha256"])
                text = output.read_text(encoding="utf-8")
                self.assertNotIn("wonderful", text)
                self.assertNotIn("aggregated_review_text", text)
                self.assertEqual(
                    hashlib.sha256(output.read_bytes()).hexdigest(),
                    summary["output_sha256"],
                )
            self.assertEqual(hashes[0], hashes[1])
            with (root / "a.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["tmdb_id"] for row in rows], ["10", "20"])
            self.assertFalse(summary["review_text_in_output"])
            self.assertFalse(summary["method_fitted_to_ratings"])

    def test_duplicate_tmdb_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = {
                "movielens_id": "1", "imdb_id": "tt1", "tmdb_id": 10,
                "release_year": 2020, "review_count": 1,
                "aggregated_review_text": "Good film.",
            }
            sample = root / "sample.jsonl"
            sample.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
            with self.assertRaisesRegex(ValueError, "Duplicate TMDB ID"):
                build_sentiment_features(sample, root / "out.csv", root / "out.json")


if __name__ == "__main__":
    unittest.main()
