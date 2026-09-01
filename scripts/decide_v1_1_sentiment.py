#!/usr/bin/env python3
"""Apply the predefined V1.1 sentiment success criteria."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.coverage_matched_modeling import (  # noqa: E402
    evaluate_coverage_matched_ridge,
)
from movie_rating_reliability.sentiment_augmented_modeling import (  # noqa: E402
    evaluate_sentiment_augmented_ridge,
)
from movie_rating_reliability.sentiment_comparison import (  # noqa: E402
    compare_sentiment_models,
)
from movie_rating_reliability.sentiment_decision import (  # noqa: E402
    apply_v1_1_success_decision,
)


def main() -> None:
    ratings = PROJECT_ROOT / "data" / "processed" / "v1_movie_ratings.csv"
    test_features = PROJECT_ROOT / "data" / "processed" / "v1_1_sentiment_features.csv"
    base = evaluate_coverage_matched_ridge(ratings, test_features)
    augmented = evaluate_sentiment_augmented_ridge(
        ratings,
        PROJECT_ROOT / "data" / "processed" / "v1_1_training_sentiment_features.csv",
        test_features,
        PROJECT_ROOT / "data" / "processed" / "v1_1_sentiment_enriched_ratings.csv",
    )
    comparison = compare_sentiment_models(base, augmented, test_features)
    decision = apply_v1_1_success_decision(comparison)
    output = PROJECT_ROOT / "reports" / "generated" / "v1_1_sentiment_decision.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(decision, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
