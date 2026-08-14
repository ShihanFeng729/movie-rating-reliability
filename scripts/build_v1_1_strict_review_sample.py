#!/usr/bin/env python3
"""Build the local-only strict text sample for V1.1."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.strict_review_sample import (  # noqa: E402
    build_strict_review_sample,
)


def main() -> None:
    summary = build_strict_review_sample(
        PROJECT_ROOT / "data" / "processed" / "v1_movie_ratings.csv",
        PROJECT_ROOT / "data" / "raw" / "tmdb" / "v1_reviews",
        PROJECT_ROOT / "data" / "processed" / "v1_1_strict_review_sample.jsonl",
        PROJECT_ROOT / "reports" / "generated" / "v1_1_strict_review_sample.json",
        cutoff=datetime(2023, 10, 13, tzinfo=timezone.utc),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
