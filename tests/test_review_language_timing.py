from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.review_language_timing import (  # noqa: E402
    audit_language_and_timing,
    classify_language,
    validate_languages_with_langdetect,
)


class ReviewLanguageTimingTests(unittest.TestCase):
    def test_conservative_language_classes(self) -> None:
        english = "This is a film that I enjoyed because the story and acting were strong."
        spanish = "Esta es una película que no es para todos, pero la historia es muy buena."
        self.assertEqual(classify_language(english)["label"], "likely_english")
        self.assertEqual(classify_language(spanish)["label"], "likely_non_english")
        self.assertEqual(classify_language("Great!")["label"], "undetermined")

    def test_audit_counts_cutoffs_without_exposing_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            raw.mkdir()
            record = {
                "payload": {"results": [
                    {
                        "content": "This is a movie that I liked and would watch again.",
                        "created_at": "2023-01-01T00:00:00Z",
                    },
                    {
                        "content": "The acting was good but the ending was not for me.",
                        "created_at": "2025-01-01T00:00:00Z",
                    },
                ]}
            }
            (raw / "42.json").write_text(json.dumps(record), encoding="utf-8")
            summary = audit_language_and_timing(
                raw,
                root / "summary.json",
                imdb_cutoff=datetime(2026, 1, 1, tzinfo=timezone.utc),
                movielens_cutoff=datetime(2023, 10, 13, tzinfo=timezone.utc),
            )
            self.assertEqual(summary["reviews_on_or_before_imdb_cutoff"], 2)
            self.assertEqual(summary["reviews_on_or_before_movielens_cutoff"], 1)
            self.assertEqual(
                summary["movies_with_reviews_on_or_before_movielens_cutoff"], 1
            )
            self.assertNotIn("acting", json.dumps(summary))
            self.assertFalse(summary["raw_review_text_published"])
            validation = validate_languages_with_langdetect(raw)
            self.assertEqual(validation["movie_majority_language_counts"], {"en": 1})


if __name__ == "__main__":
    unittest.main()
