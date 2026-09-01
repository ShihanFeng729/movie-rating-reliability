"""Same-sample reporting for base and sentiment-augmented V1.1 Ridge."""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import fmean
from typing import Any

from .modeling import regression_metrics


TIME_GROUPS = (
    ("2015–2016", 2015, 2016),
    ("2017–2018", 2017, 2018),
    ("2019–2020", 2019, 2020),
    ("2021–2022", 2021, 2022),
)


def compare_sentiment_models(
    base: dict[str, Any],
    augmented: dict[str, Any],
    test_features_path: Path,
    *,
    full_outer_test_count: int = 189,
    training_movie_count: int = 752,
    training_sentiment_available_count: int = 325,
) -> dict[str, Any]:
    """Compare two prediction reports after enforcing exact row identity."""

    base_rows = _index_predictions(base)
    augmented_rows = _index_predictions(augmented)
    base_id_hash = base.get("coverage_movie_ids_sha256")
    augmented_id_hash = augmented.get("outer_test_movie_ids_sha256")
    if base_id_hash and augmented_id_hash and base_id_hash != augmented_id_hash:
        raise ValueError("Base and augmented frozen movie-ID hashes differ.")
    if set(base_rows) != set(augmented_rows):
        raise ValueError("Base and augmented outer-test movie IDs differ.")
    ordered_ids = sorted(base_rows)
    for movie_id in ordered_ids:
        base_row = base_rows[movie_id]
        augmented_row = augmented_rows[movie_id]
        if (
            base_row["actual"] != augmented_row["actual"]
            or base_row["release_year"] != augmented_row["release_year"]
        ):
            raise ValueError(f"Outcome or year mismatch for movie {movie_id}.")

    features = _read_features(test_features_path)
    if set(features) != set(base_rows):
        raise ValueError("Sentiment feature IDs do not match comparison movies.")
    overall = _metric_comparison(
        [base_rows[movie_id] for movie_id in ordered_ids],
        [augmented_rows[movie_id] for movie_id in ordered_ids],
    )
    subgroup_rows = []
    for label, start_year, end_year in TIME_GROUPS:
        ids = [
            movie_id for movie_id in ordered_ids
            if start_year <= int(base_rows[movie_id]["release_year"]) <= end_year
        ]
        if len(ids) < 2:
            raise ValueError(f"Time subgroup {label} has fewer than two movies.")
        comparison = _metric_comparison(
            [base_rows[movie_id] for movie_id in ids],
            [augmented_rows[movie_id] for movie_id in ids],
        )
        improvement = comparison["mae_improvement_base_minus_augmented"]
        subgroup_rows.append({
            "group": label,
            "start_year": start_year,
            "end_year": end_year,
            "movie_count": len(ids),
            **comparison,
            "mae_direction": (
                "improved" if improvement > 0
                else "worsened" if improvement < 0 else "tied"
            ),
        })
    improved_groups = sum(row["mae_direction"] == "improved" for row in subgroup_rows)
    feature_rows = list(features.values())
    return {
        "stage": "v1_1_same_sample_sentiment_comparison",
        "comparison_movie_count": len(ordered_ids),
        "full_outer_test_movie_count": full_outer_test_count,
        "strict_test_coverage_rate": round(
            len(ordered_ids) / full_outer_test_count, 4
        ),
        "training_movie_count": training_movie_count,
        "training_sentiment_available_count": training_sentiment_available_count,
        "training_sentiment_coverage_rate": round(
            training_sentiment_available_count / training_movie_count, 4
        ),
        "same_movie_ids_verified": True,
        "same_actual_values_verified": True,
        "same_release_years_verified": True,
        "outer_test_movie_ids_sha256": base_id_hash or augmented_id_hash or "",
        "overall": overall,
        "predefined_time_groups": subgroup_rows,
        "time_group_count": len(subgroup_rows),
        "time_groups_with_mae_improvement": improved_groups,
        "test_review_count_total": sum(int(row["review_count"]) for row in feature_rows),
        "test_review_count_mean_per_movie": round(
            fmean(int(row["review_count"]) for row in feature_rows), 4
        ),
        "test_token_count_total": sum(int(row["token_count"]) for row in feature_rows),
        "test_token_count_mean_per_movie": round(
            fmean(int(row["token_count"]) for row in feature_rows), 4
        ),
        "test_movies_without_lexicon_hits": sum(
            int(row["lexicon_hits"]) == 0 for row in feature_rows
        ),
        "predefined_success_thresholds": {
            "minimum_overall_mae_improvement": 0.01,
            "minimum_improved_time_groups": 3,
            "time_group_total": 4,
        },
        "success_decision_applied": False,
        "interpretation_note": (
            "This report presents the fixed comparison evidence. The next stage "
            "applies the predefined success decision without changing the models."
        ),
    }


def _metric_comparison(
    base_rows: list[dict[str, Any]], augmented_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    actual = [float(row["actual"]) for row in base_rows]
    base_predictions = [float(row["prediction"]) for row in base_rows]
    augmented_predictions = [float(row["prediction"]) for row in augmented_rows]
    base_metrics = _rounded(regression_metrics(actual, base_predictions))
    augmented_metrics = _rounded(regression_metrics(actual, augmented_predictions))
    improvement = round(base_metrics["mae"] - augmented_metrics["mae"], 4)
    return {
        "base_ridge": base_metrics,
        "sentiment_ridge": augmented_metrics,
        "mae_improvement_base_minus_augmented": improvement,
        "mae_change_augmented_minus_base": round(-improvement, 4),
    }


def _index_predictions(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = report.get("outer_test_predictions", [])
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        movie_id = str(row["movielens_id"])
        if movie_id in indexed:
            raise ValueError(f"Duplicate prediction movie ID {movie_id}.")
        indexed[movie_id] = row
    if not indexed:
        raise ValueError("Prediction report contains no outer-test rows.")
    return indexed


def _read_features(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"movielens_id", "review_count", "token_count", "lexicon_hits"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Test sentiment features are missing reporting columns.")
    indexed = {row["movielens_id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Test sentiment features contain duplicate movie IDs.")
    return indexed


def _rounded(metrics: dict[str, float]) -> dict[str, float]:
    return {key: round(value, 4) for key, value in metrics.items()}
