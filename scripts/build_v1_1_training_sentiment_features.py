#!/usr/bin/env python3
"""Freeze strict training reviews and build local sentiment features."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.sentiment_baseline import (  # noqa: E402
    build_sentiment_features,
)
from movie_rating_reliability.strict_review_sample import (  # noqa: E402
    build_strict_review_sample,
)


def main() -> None:
    strict_summary = build_strict_review_sample(
        PROJECT_ROOT / "data" / "processed" / "v1_movie_ratings.csv",
        PROJECT_ROOT / "data" / "raw" / "tmdb" / "v1_1_training_reviews",
        PROJECT_ROOT / "data" / "processed" / "v1_1_training_strict_reviews.jsonl",
        PROJECT_ROOT / "reports" / "generated" / "v1_1_training_strict_reviews.json",
        cutoff=datetime(2023, 10, 13, tzinfo=timezone.utc),
    )
    sentiment_summary = build_sentiment_features(
        PROJECT_ROOT / "data" / "processed" / "v1_1_training_strict_reviews.jsonl",
        PROJECT_ROOT / "data" / "processed" / "v1_1_training_sentiment_features.csv",
        PROJECT_ROOT / "reports" / "generated" / "v1_1_training_sentiment_features.json",
    )
    print(json.dumps({
        "strict_sample": strict_summary,
        "sentiment_features": sentiment_summary,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
