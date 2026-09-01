#!/usr/bin/env python3
"""Evaluate the fixed sentiment-augmented Ridge on the matched holdout."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.sentiment_augmented_modeling import (  # noqa: E402
    evaluate_sentiment_augmented_ridge,
)


def main() -> None:
    result = evaluate_sentiment_augmented_ridge(
        PROJECT_ROOT / "data" / "processed" / "v1_movie_ratings.csv",
        PROJECT_ROOT / "data" / "processed" / "v1_1_training_sentiment_features.csv",
        PROJECT_ROOT / "data" / "processed" / "v1_1_sentiment_features.csv",
        PROJECT_ROOT / "data" / "processed" / "v1_1_sentiment_enriched_ratings.csv",
    )
    output = PROJECT_ROOT / "reports" / "generated" / "v1_1_sentiment_ridge.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    printable = {key: result[key] for key in (
        "train_movie_count", "test_movie_count", "ridge_alpha", "model_metrics",
        "training_sentiment_available_count", "training_sentiment_missing_count",
        "test_sentiment_available_count", "sentiment_feature_used_by_model",
        "outer_test_used_for_sentiment_preprocessing",
    )}
    print(json.dumps(printable, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
