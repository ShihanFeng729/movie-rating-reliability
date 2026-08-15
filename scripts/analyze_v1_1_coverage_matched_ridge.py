#!/usr/bin/env python3
"""Evaluate base Ridge on the strict V1.1 text-coverage holdout."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.coverage_matched_modeling import (  # noqa: E402
    evaluate_coverage_matched_ridge,
)


def main() -> None:
    result = evaluate_coverage_matched_ridge(
        PROJECT_ROOT / "data" / "processed" / "v1_movie_ratings.csv",
        PROJECT_ROOT / "data" / "processed" / "v1_1_sentiment_features.csv",
    )
    output = (
        PROJECT_ROOT
        / "reports"
        / "generated"
        / "v1_1_coverage_matched_ridge.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    printable = {
        key: result[key]
        for key in (
            "train_movie_count", "full_outer_test_movie_count", "test_movie_count",
            "test_year_min", "test_year_max", "ridge_alpha", "model_metrics",
            "baselines", "sentiment_feature_used_by_model",
        )
    }
    print(json.dumps(printable, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
