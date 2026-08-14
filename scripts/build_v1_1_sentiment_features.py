#!/usr/bin/env python3
"""Build local V1.1 features from the frozen strict review sample."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.sentiment_baseline import (  # noqa: E402
    build_sentiment_features,
)


def main() -> None:
    summary = build_sentiment_features(
        PROJECT_ROOT / "data" / "processed" / "v1_1_strict_review_sample.jsonl",
        PROJECT_ROOT / "data" / "processed" / "v1_1_sentiment_features.csv",
        PROJECT_ROOT / "reports" / "generated" / "v1_1_sentiment_baseline.json",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
